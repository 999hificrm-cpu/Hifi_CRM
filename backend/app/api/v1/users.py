from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user, require_org_admin, get_tenant_id
from app.models.user import User
from app.models.audit import AuditLog
from app.models.organization import Subscription
from app.schemas.user import UserCreate, UserUpdate, UserOut
from app.core.security import get_password_hash
from app.core.business_time import organization_business_date

router = APIRouter(prefix="/users", tags=["Users & RBAC"])


@router.get("/", response_model=List[UserOut])
def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    if not (current_user.is_org_admin or current_user.tenant_role == "SALES_MANAGER"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager or Organization Admin privilege required")
    query = db.query(User).filter(User.organization_id == tenant_id)
    return query.order_by(User.full_name.asc()).offset(skip).limit(limit).all()


@router.get("/telecallers")
def list_organization_telecallers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    if not (current_user.is_org_admin or current_user.tenant_role == "SALES_MANAGER"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager or Organization Admin privilege required")
    from app.models.lead import Lead
    telecallers = db.query(User).filter(
        User.organization_id == tenant_id,
        User.tenant_role == "TELECALLER"
    ).order_by(User.full_name.asc()).all()

    from app.models.telecaller_target import TelecallerTarget
    today = organization_business_date(db, tenant_id)
    result = []
    for t in telecallers:
        assigned_count = db.query(Lead).filter(
            Lead.owner_id == t.id,
            Lead.organization_id == tenant_id
        ).count()
        target = db.query(TelecallerTarget).filter(
            TelecallerTarget.organization_id == tenant_id,
            TelecallerTarget.user_id == t.id,
            TelecallerTarget.target_date == today,
        ).first()
        result.append({
            "id": t.id,
            "full_name": t.full_name,
            "email": t.email,
            "phone": t.phone,
            "status": t.status,
            "assigned_leads_count": assigned_count,
            "telecaller_targets": {
                "calls": target.target_calls,
                "connects": target.target_connects,
                "talk_time": target.target_talk_time_minutes,
                "conversions": target.target_conversions,
            } if target else {"calls": 0, "connects": 0, "talk_time": 0, "conversions": 0},
            "created_at": t.created_at.isoformat() if t.created_at else None
        })
    return result


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_tenant_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
    tenant_id: str = Depends(get_tenant_id)
):
    email_clean = data.email.lower().strip()
    existing = db.query(User).filter(
        User.email == email_clean,
        User.organization_id == tenant_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {data.email} already exists in this organization"
        )

    # Validate allowed roles
    allowed_roles = ["ORG_ADMIN", "SALES_MANAGER", "SALES_REP", "TELECALLER", "VIEWER"]
    role = data.tenant_role or "SALES_REP"
    if role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid tenant role: {role}")

    # Check seat limit
    active_user_count = db.query(User).filter(
        User.organization_id == tenant_id,
        User.status == "ACTIVE",
        User.deleted_at.is_(None)
    ).count()
    
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == tenant_id,
        Subscription.status == "ACTIVE"
    ).first()
    
    if subscription and active_user_count >= subscription.seats_purchased:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Seat limit exceeded. Your plan allows up to {subscription.seats_purchased} active users."
        )

    user = User(
        organization_id=tenant_id,
        tenant_role=role,
        full_name=data.full_name.strip(),
        email=email_clean,
        phone=data.phone,
        password_hash=get_password_hash(data.password),
        status="ACTIVE",
        # Tenant administrators manage tenant roles only. Platform permissions
        # are assigned through the platform RBAC administration boundary.
        permission_overrides={}
    )
    db.add(user)
    db.flush()

    audit = AuditLog(
        organization_id=tenant_id,
        user_id=current_user.id,
        action="USER_INVITED",
        entity_type="USER",
        entity_id=user.id,
        new_values={"email": user.email, "role": user.tenant_role}
    )
    db.add(audit)
    db.commit()
    try:
        db.refresh(user)
    except Exception:
        pass
    return user


@router.patch("/{id}", response_model=UserOut)
def update_user(
    id: str,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
    tenant_id: str = Depends(get_tenant_id)
):
    user = db.query(User).filter(
        User.id == id,
        User.organization_id == tenant_id
    ).with_for_update().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    old_role = user.tenant_role
    if data.full_name:
        user.full_name = data.full_name.strip()
    if data.phone is not None:
        user.phone = data.phone
    if data.tenant_role:
        user.tenant_role = data.tenant_role
    if data.status:
        user.status = data.status
    if data.permission_overrides is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization administrators cannot modify platform permission overrides",
        )
    if data.telecaller_targets is not None:
        from app.models.telecaller_target import TelecallerTarget
        if user.tenant_role != "TELECALLER":
            raise HTTPException(status_code=400, detail="Daily targets can only be configured for telecallers")
        values = data.telecaller_targets
        target_date = organization_business_date(db, tenant_id)
        numeric_values = {
            "target_calls": int(values.get("calls", values.get("target_calls", 0)) or 0),
            "target_connects": int(values.get("connects", values.get("target_connects", 0)) or 0),
            "target_talk_time_minutes": int(values.get("talk_time", values.get("target_talk_time_minutes", 0)) or 0),
            "target_qualified_leads": int(values.get("qualified_leads", values.get("target_qualified_leads", 0)) or 0),
            "target_conversions": int(values.get("conversions", values.get("target_conversions", 0)) or 0),
            "target_revenue": float(values.get("revenue", values.get("target_revenue", 0)) or 0),
        }
        if any(value < 0 for value in numeric_values.values()):
            raise HTTPException(status_code=422, detail="Target values cannot be negative")
        target = db.query(TelecallerTarget).filter(
            TelecallerTarget.organization_id == tenant_id,
            TelecallerTarget.user_id == user.id,
            TelecallerTarget.target_date == target_date,
        ).first()
        if not target:
            target = TelecallerTarget(
                id=str(__import__('uuid').uuid4()), organization_id=tenant_id,
                user_id=user.id, target_date=target_date,
            )
            db.add(target)
        for field, value in numeric_values.items():
            setattr(target, field, value)
        # The legacy JSON is deliberately not updated: TelecallerTarget is the
        # authoritative store.  Existing JSON is read only once for migration.

    audit = AuditLog(
        organization_id=tenant_id,
        user_id=current_user.id,
        action="USER_UPDATED",
        entity_type="USER",
        entity_id=user.id,
        old_values={"role": old_role},
        new_values={"role": user.tenant_role, "status": user.status}
    )
    db.add(audit)
    db.commit()
    try:
        db.refresh(user)
    except Exception:
        pass
    return user
