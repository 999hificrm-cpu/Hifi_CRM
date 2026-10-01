from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header

from sqlalchemy.orm import Session
from pydantic import BaseModel, Field


from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.models.global_registry import GlobalCompany
from app.models.global_people import GlobalPerson
from app.schemas.user import UserOut, UserCreate
from app.core.security import get_password_hash

router = APIRouter(prefix="/admin", tags=["Super Admin"])

def require_super_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin privileges required"
        )
    return current_user


from app.models.call_record import CallRecord
from app.models.session import AttendanceSession
from app.models.company import Company
from app.models.contact import Contact
from app.core.business_time import organization_business_date, organization_day_bounds_utc
from datetime import datetime, timezone

class KPIDashboardOut(BaseModel):
    total_organizations: int
    total_org_admins: int
    total_global_companies: int
    total_people_leads: int
    total_data_pulls: int
    total_calls_today: int
    active_telecaller_sessions: int
    total_talk_time_minutes: int


@router.get("/kpis", response_model=KPIDashboardOut)
def get_kpis(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    total_orgs = db.query(Organization).count()
    total_admins = db.query(User).filter(User.tenant_role == "ORG_ADMIN").count()
    total_companies = db.query(GlobalCompany).filter(GlobalCompany.status == "ACTIVE").count()
    total_people = db.query(GlobalPerson).filter(GlobalPerson.status == "ACTIVE").count()
    total_pulls = (
        db.query(Company).filter(Company.source_global_company_id.isnot(None)).count()
        + db.query(Contact).filter(Contact.source_global_contact_id.isnot(None)).count()
    )

    # Each tenant's "today" is evaluated in its configured business timezone.
    from sqlalchemy import func
    total_calls_today = 0
    talk_time_seconds = 0
    for org in db.query(Organization).all():
        business_date = organization_business_date(db, org.id)
        day_start, day_end = organization_day_bounds_utc(db, org.id, business_date)
        total_calls_today += db.query(CallRecord).filter(
            CallRecord.organization_id == org.id,
            CallRecord.started_at >= day_start,
            CallRecord.started_at <= day_end,
            CallRecord.disposition != "INITIATED",
        ).count()
        talk_time_seconds += db.query(func.sum(CallRecord.duration_seconds)).filter(
            CallRecord.organization_id == org.id,
            CallRecord.started_at >= day_start,
            CallRecord.started_at <= day_end,
        ).scalar() or 0

    active_sessions = db.query(AttendanceSession).filter(
        AttendanceSession.logout_at.is_(None)
    ).count()

    return KPIDashboardOut(
        total_organizations=total_orgs,
        total_org_admins=total_admins,
        total_global_companies=total_companies,
        total_people_leads=total_people,
        total_data_pulls=total_pulls,
        total_calls_today=total_calls_today,
        active_telecaller_sessions=active_sessions,
        total_talk_time_minutes=talk_time_seconds // 60
    )


class AdminUserOut(UserOut):
    organization_name: Optional[str] = None


@router.get("/users", response_model=List[AdminUserOut])
def list_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    # Fetch all non-deleted users (especially ORG_ADMIN and DATA_ENTRY)
    users = db.query(User, Organization.name).outerjoin(
        Organization, User.organization_id == Organization.id
    ).filter(
        User.deleted_at.is_(None)
    ).order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for u, org_name in users:
        u_dict = {k: v for k, v in u.__dict__.items() if not k.startswith("_")}
        u_dict["organization_name"] = org_name
        result.append(AdminUserOut(**u_dict))
    return result


class AdminUserCreate(UserCreate):
    pass

class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    platform_role: Optional[str] = None
    tenant_role: Optional[str] = None
    password: Optional[str] = None


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    data: AdminUserCreate,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    email_clean = data.email.lower().strip()
    existing = db.query(User).filter(User.email == email_clean).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {data.email} already exists"
        )
        
    user = User(
        organization_id=data.organization_id,
        platform_role=data.platform_role,
        tenant_role=data.tenant_role,
        full_name=data.full_name.strip(),
        email=email_clean,
        phone=data.phone,
        password_hash=get_password_hash(data.password),
        status="ACTIVE",
        token_version=1
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    from app.services.audit_service import audit_service
    client_ip = http_request.client.host if http_request.client else "Unknown"
    user_agent = http_request.headers.get("user-agent", "Unknown")
    audit_service.record(
        db=db,
        action="USER_CREATED",
        entity_type="USER",
        entity_id=user.id,
        actor_user_id=current_user.id,
        target_user_id=user.id,
        organization_id=user.organization_id,
        new_values={"email": user.email, "platform_role": user.platform_role, "tenant_role": user.tenant_role},
        ip_address=client_ip,
        user_agent=user_agent
    )

    return user


class UserStatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = "Status updated by platform administrator"


@router.patch("/users/{user_id}/status", response_model=UserOut)
def update_user_status(
    user_id: str,
    data: UserStatusUpdate,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own status")
        
    old_status = user.status
    user.status = data.status

    # Immediate session revocation on suspension or deactivation (Problems #15, #18)
    if data.status in ("SUSPENDED", "DEACTIVATED"):
        user.token_version = (user.token_version or 1) + 1

    db.commit()
    db.refresh(user)

    from app.services.audit_service import audit_service
    client_ip = http_request.client.host if http_request.client else "Unknown"
    user_agent = http_request.headers.get("user-agent", "Unknown")
    audit_service.record(
        db=db,
        action="USER_STATUS_CHANGED",
        entity_type="USER",
        entity_id=user.id,
        actor_user_id=current_user.id,
        target_user_id=user.id,
        organization_id=user.organization_id,
        old_values={"status": old_status},
        new_values={"status": user.status, "token_version": user.token_version},
        reason=data.reason,
        ip_address=client_ip,
        user_agent=user_agent
    )

    return user


@router.delete("/users/{user_id}")
def delete_admin_user(
    user_id: str,
    http_request: Request,
    reason: Optional[str] = "Deactivated by administrator",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Soft-deletes a user and invalidates all active sessions (Problems #10, #42).
    Preserves historical call logs, tasks, and audit history.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")

    user.deleted_at = datetime.now(timezone.utc)
    user.deleted_by = current_user.id
    user.deletion_reason = reason
    user.status = "DEACTIVATED"
    user.token_version = (user.token_version or 1) + 1
    db.commit()

    from app.services.audit_service import audit_service
    client_ip = http_request.client.host if http_request.client else "Unknown"
    user_agent = http_request.headers.get("user-agent", "Unknown")
    audit_service.record(
        db=db,
        action="USER_DELETED",
        entity_type="USER",
        entity_id=user.id,
        actor_user_id=current_user.id,
        target_user_id=user.id,
        organization_id=user.organization_id,
        old_values={"email": user.email, "status": "ACTIVE"},
        new_values={"deleted_at": user.deleted_at.isoformat(), "status": "DEACTIVATED"},
        reason=reason,
        ip_address=client_ip,
        user_agent=user_agent
    )

    return {"success": True, "message": f"User {user.email} moved to Recycle Bin. Sessions invalidated."}


@router.patch("/users/{user_id}", response_model=UserOut)
def update_admin_user(
    user_id: str,
    data: AdminUserUpdate,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    old_values = {}
    new_values = {}

    if data.email:
        email_clean = data.email.lower().strip()
        if email_clean != user.email:
            existing = db.query(User).filter(User.email == email_clean).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
            old_values["email"] = user.email
            user.email = email_clean
            new_values["email"] = email_clean

    if data.full_name:
        old_values["full_name"] = user.full_name
        user.full_name = data.full_name.strip()
        new_values["full_name"] = user.full_name
    if data.phone is not None:
        old_values["phone"] = user.phone
        user.phone = data.phone
        new_values["phone"] = data.phone
    if data.platform_role is not None:
        old_values["platform_role"] = user.platform_role
        user.platform_role = data.platform_role
        new_values["platform_role"] = data.platform_role
        # Invalidate session if platform role changed
        user.token_version = (user.token_version or 1) + 1
    if data.tenant_role is not None:
        old_values["tenant_role"] = user.tenant_role
        user.tenant_role = data.tenant_role
        new_values["tenant_role"] = data.tenant_role
        user.token_version = (user.token_version or 1) + 1
    if data.password:
        user.password_hash = get_password_hash(data.password)
        user.token_version = (user.token_version or 1) + 1
        new_values["password_changed"] = True

    db.commit()
    db.refresh(user)

    from app.services.audit_service import audit_service
    client_ip = http_request.client.host if http_request.client else "Unknown"
    user_agent = http_request.headers.get("user-agent", "Unknown")
    audit_service.record(
        db=db,
        action="USER_UPDATED",
        entity_type="USER",
        entity_id=user.id,
        actor_user_id=current_user.id,
        target_user_id=user.id,
        organization_id=user.organization_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=client_ip,
        user_agent=user_agent
    )

    return user


class SuspendOrganizationRequest(BaseModel):
    reason: str = Field(min_length=5, description="Mandatory justification for suspending tenant")


@router.post("/organizations/{org_id}/suspend")
def suspend_organization(
    org_id: str,
    data: SuspendOrganizationRequest,
    http_request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Safely suspends an organization and revokes all tenant sessions (Problems #9, #15, #50).
    Requires explicit reason and supports Idempotency-Key.
    """
    from app.services.idempotency_service import idempotency_service

    # Check idempotency
    cached = idempotency_service.check_and_get(
        db=db,
        key=idempotency_key,
        user_id=current_user.id,
        action="ORG_SUSPEND",
        request_payload={"org_id": org_id, "reason": data.reason}
    )
    if cached:
        return cached[1]

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    old_status = org.status
    org.status = "SUSPENDED"

    # Immediately revoke all user sessions in this organization (Problem #15)
    users = db.query(User).filter(User.organization_id == org.id).all()
    for u in users:
        u.token_version = (u.token_version or 1) + 1

    db.commit()

    # Record Audit Event
    from app.services.audit_service import audit_service
    client_ip = http_request.client.host if http_request.client else "Unknown"
    user_agent = http_request.headers.get("user-agent", "Unknown")
    audit_service.record(
        db=db,
        action="ORGANIZATION_SUSPENDED",
        entity_type="ORGANIZATION",
        entity_id=org.id,
        actor_user_id=current_user.id,
        organization_id=org.id,
        old_values={"status": old_status},
        new_values={"status": "SUSPENDED", "revoked_user_count": len(users)},
        reason=data.reason,
        ip_address=client_ip,
        user_agent=user_agent
    )

    response_body = {
        "success": True,
        "message": f"Organization '{org.name}' suspended. {len(users)} user sessions invalidated.",
        "organization_id": org.id,
        "status": "SUSPENDED",
        "revoked_sessions_count": len(users)
    }

    # Save to idempotency store
    idempotency_service.save(
        db=db,
        key=idempotency_key,
        user_id=current_user.id,
        action="ORG_SUSPEND",
        request_payload={"org_id": org_id, "reason": data.reason},
        response_status=200,
        response_body=response_body
    )

    return response_body


@router.get("/organizations/{id}/schema/inspect")
def inspect_organization_schema(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    org = db.query(Organization).filter(Organization.id == id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    schema_name = org.schema_name
    if not schema_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Organization has no isolated schema")

    # SQLite fallback
    if db.bind and db.bind.dialect.name == "sqlite":
        return {"dialect": "sqlite", "tables": "SQLite does not support isolated schemas per tenant natively. All data is in the main database."}

    # Postgres
    from sqlalchemy import text
    try:
        tables = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = :schema_name"), {"schema_name": schema_name}).fetchall()
        table_stats = []
        for (tbl,) in tables:
            count = db.execute(text(f'SELECT count(*) FROM "{schema_name}"."{tbl}"')).scalar()
            table_stats.append({"table_name": tbl, "row_count": count})
        return {"dialect": "postgresql", "schema": schema_name, "tables": table_stats}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/organizations/{id}/audit/export")
def export_organization_audit_logs(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    import csv
    import io
    from fastapi.responses import StreamingResponse
    from app.models.audit import AuditLog

    org = db.query(Organization).filter(Organization.id == id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    logs = db.query(AuditLog).filter(AuditLog.organization_id == id).order_by(AuditLog.created_at.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "User ID", "Action", "Entity Type", "Entity ID", "Reason", "IP Address", "Created At"])
    
    for log in logs:
        writer.writerow([
            log.id,
            log.user_id,
            log.action,
            log.entity_type,
            log.entity_id,
            log.reason,
            log.ip_address,
            log.created_at.isoformat() if log.created_at else ""
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]), 
        media_type="text/csv", 
        headers={"Content-Disposition": f"attachment; filename=audit_logs_{org.slug}.csv"}
    )


@router.post("/organizations/{id}/trial")
def start_organization_trial(
    id: str,
    days: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Grants a trial period to the organization (default 3 days).
    Controlled explicitly by Super Admin.
    """
    from app.services.billing_service import start_trial
    
    org = db.query(Organization).filter(Organization.id == id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        
    try:
        sub = start_trial(db, organization_id=id, days=days)
        return {
            "success": True, 
            "message": f"{days}-day trial started for {org.name}.",
            "subscription": {
                "id": sub.id,
                "status": sub.status,
                "current_period_start": sub.current_period_start,
                "current_period_end": sub.current_period_end
            }
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/organizations/{id}/full-access")
def grant_full_access_to_organization(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Grants 10-year full enterprise access to the organization.
    """
    from app.services.billing_service import grant_full_access
    
    org = db.query(Organization).filter(Organization.id == id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        
    try:
        sub = grant_full_access(db, organization_id=id)
        return {
            "success": True, 
            "message": f"Full 10-year enterprise access granted for {org.name}.",
            "subscription": {
                "id": sub.id,
                "status": sub.status,
                "current_period_start": sub.current_period_start,
                "current_period_end": sub.current_period_end
            }
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
