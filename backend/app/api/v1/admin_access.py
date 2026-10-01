from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_super_admin, require_platform_permission
from app.core.security import create_support_token
from app.models.user import User
from app.models.organization import Organization
from app.models.rbac import PlatformRole, Permission, RolePermission, PlatformUserRole
from app.models.support import SupportSession
from app.services.audit_service import audit_service

router = APIRouter(prefix="/admin", tags=["Admin Access & Security"])


# --- Schemas ---

class PermissionOut(BaseModel):
    id: str
    code: str
    name: str
    category: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class PlatformRoleOut(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    is_system: bool
    permissions: List[str] = []

    class Config:
        from_attributes = True


class AssignRoleRequest(BaseModel):
    user_id: str
    role_code: str
    reason: Optional[str] = Field(default="Assigned by administrator")


class UserPermissionOverrideRequest(BaseModel):
    user_id: str
    permission_code: str
    granted: bool
    reason: Optional[str] = Field(default="Administrator override")


class RevokeSessionRequest(BaseModel):
    user_id: str
    reason: Optional[str] = Field(default="Security revocation")


class CreateSupportSessionRequest(BaseModel):
    organization_id: str
    target_user_id: Optional[str] = None
    reason: str = Field(min_length=5, description="Mandatory justification for accessing tenant scope")
    duration_minutes: int = Field(default=15, ge=1, le=120)


class SupportSessionOut(BaseModel):
    id: str
    created_by: str
    actor_name: Optional[str] = None
    target_user_id: Optional[str] = None
    target_user_name: Optional[str] = None
    organization_id: str
    organization_name: Optional[str] = None
    reason: str
    started_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    is_active: bool
    support_token: Optional[str] = None

    class Config:
        from_attributes = True


# --- Endpoints ---

@router.get("/access/permissions", response_model=List[PermissionOut])
def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_permission("PLATFORM_USER_READ"))
):
    """Lists all registered platform permissions."""
    return db.query(Permission).order_by(Permission.category, Permission.code).all()


@router.get("/access/roles", response_model=List[PlatformRoleOut])
def list_platform_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_permission("PLATFORM_USER_READ"))
):
    """Lists all platform roles with their assigned permission codes."""
    roles = db.query(PlatformRole).all()
    results = []
    for r in roles:
        perm_codes = [p.code for p in r.permissions]
        results.append(
            PlatformRoleOut(
                id=r.id,
                code=r.code,
                name=r.name,
                description=r.description,
                is_system=r.is_system,
                permissions=perm_codes
            )
        )
    return results


@router.post("/access/assign-role")
def assign_platform_role(
    req: AssignRoleRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Assigns a platform role to a user and logs an audited ROLE_ASSIGNED event (Problems #17, #18).
    """
    target_user = db.query(User).filter(User.id == req.user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    role = db.query(PlatformRole).filter(PlatformRole.code == req.role_code).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role '{req.role_code}' not found")

    existing = db.query(PlatformUserRole).filter(
        PlatformUserRole.user_id == target_user.id,
        PlatformUserRole.role_id == role.id
    ).first()

    old_role = target_user.platform_role
    if not existing:
        pur = PlatformUserRole(
            user_id=target_user.id,
            role_id=role.id,
            assigned_by=current_user.id
        )
        db.add(pur)

    target_user.platform_role = role.code
    # Invalidate existing sessions so new permissions take immediate effect
    target_user.token_version = (target_user.token_version or 1) + 1
    db.commit()

    # Centralized Audit (Problem #18)
    client_ip = http_request.client.host if http_request.client else "Unknown"
    user_agent = http_request.headers.get("user-agent", "Unknown")
    audit_service.record(
        db=db,
        action="ROLE_ASSIGNED",
        entity_type="USER",
        entity_id=target_user.id,
        actor_user_id=current_user.id,
        target_user_id=target_user.id,
        old_values={"platform_role": old_role},
        new_values={"platform_role": role.code, "role_id": role.id},
        reason=req.reason,
        ip_address=client_ip,
        user_agent=user_agent
    )

    return {
        "success": True,
        "message": f"Assigned role '{role.code}' to user {target_user.email}",
        "user_id": target_user.id,
        "platform_role": target_user.platform_role
    }


@router.post("/access/permission-override")
def set_permission_override(
    req: UserPermissionOverrideRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Enables or revokes a specific platform permission override for an individual user (Problem #18).
    """
    target_user = db.query(User).filter(User.id == req.user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    perm = db.query(Permission).filter(Permission.code == req.permission_code).first()
    if not perm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission code not recognized")

    overrides = dict(target_user.permission_overrides or {})
    old_val = overrides.get(req.permission_code)
    overrides[req.permission_code] = req.granted
    target_user.permission_overrides = overrides
    target_user.token_version = (target_user.token_version or 1) + 1
    db.commit()

    action = "PERMISSION_GRANTED" if req.granted else "PERMISSION_REVOKED"
    client_ip = http_request.client.host if http_request.client else "Unknown"
    user_agent = http_request.headers.get("user-agent", "Unknown")
    audit_service.record(
        db=db,
        action=action,
        entity_type="USER",
        entity_id=target_user.id,
        actor_user_id=current_user.id,
        target_user_id=target_user.id,
        old_values={"permission": req.permission_code, "granted": old_val},
        new_values={"permission": req.permission_code, "granted": req.granted},
        reason=req.reason,
        ip_address=client_ip,
        user_agent=user_agent
    )

    return {"success": True, "permission_overrides": target_user.permission_overrides}


@router.post("/access/revoke-sessions")
def revoke_user_sessions(
    req: RevokeSessionRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_permission("PLATFORM_USER_SUSPEND"))
):
    """
    Immediately invalidates all active sessions/tokens for a user by bumping token_version (Problems #15, #18).
    """
    target_user = db.query(User).filter(User.id == req.user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    target_user.token_version = (target_user.token_version or 1) + 1
    db.commit()

    client_ip = http_request.client.host if http_request.client else "Unknown"
    user_agent = http_request.headers.get("user-agent", "Unknown")
    audit_service.record(
        db=db,
        action="SESSIONS_REVOKED",
        entity_type="USER",
        entity_id=target_user.id,
        actor_user_id=current_user.id,
        target_user_id=target_user.id,
        reason=req.reason,
        ip_address=client_ip,
        user_agent=user_agent
    )

    return {
        "success": True,
        "message": f"All sessions invalidated for user {target_user.email}. Next request will be denied.",
        "new_token_version": target_user.token_version
    }


# --- Support & Impersonation Sessions (Problems #19, #20, #46) ---

@router.post("/support/session", response_model=SupportSessionOut)
def create_support_session(
    req: CreateSupportSessionRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_permission("PLATFORM_SUPPORT"))
):
    """
    Generates a cryptographically signed, short-lived (default 15-min) support token.
    Enforces mandatory justification reason and dual-identity audit trail.
    """
    org = db.query(Organization).filter(Organization.id == req.organization_id).first()
    if not org or org.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target organization not found")

    target_user = None
    if req.target_user_id:
        target_user = db.query(User).filter(User.id == req.target_user_id).first()
        if not target_user or target_user.organization_id != org.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target user does not belong to specified organization")

    client_ip = http_request.client.host if http_request.client else "Unknown"
    user_agent = http_request.headers.get("user-agent", "Unknown")

    session = SupportSession(
        created_by=current_user.id,
        target_user_id=target_user.id if target_user else None,
        organization_id=org.id,
        reason=req.reason.strip(),
        started_at=datetime.now(timezone.utc),
        ip_address=client_ip,
        user_agent=user_agent
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Generate cryptographically signed support token
    token = create_support_token(
        actor_user_id=current_user.id,
        organization_id=org.id,
        support_session_id=session.id,
        target_user_id=target_user.id if target_user else None,
        expires_minutes=req.duration_minutes
    )

    # Audit the support session start
    audit_service.record(
        db=db,
        action="SUPPORT_SESSION_CREATED",
        entity_type="ORGANIZATION",
        entity_id=org.id,
        actor_user_id=current_user.id,
        target_user_id=target_user.id if target_user else None,
        organization_id=org.id,
        support_session_id=session.id,
        reason=req.reason,
        ip_address=client_ip,
        user_agent=user_agent
    )

    return SupportSessionOut(
        id=session.id,
        created_by=session.created_by,
        actor_name=current_user.full_name,
        target_user_id=session.target_user_id,
        target_user_name=target_user.full_name if target_user else None,
        organization_id=session.organization_id,
        organization_name=org.name,
        reason=session.reason,
        started_at=session.started_at,
        expires_at=session.expires_at,
        revoked_at=session.revoked_at,
        is_active=session.is_active,
        support_token=token
    )


@router.post("/support/session/{session_id}/revoke")
def revoke_support_session(
    session_id: str,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_permission("PLATFORM_SUPPORT"))
):
    """Terminates an active support session immediately."""
    session = db.query(SupportSession).filter(SupportSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support session not found")

    session.revoked_at = datetime.now(timezone.utc)
    db.commit()

    client_ip = http_request.client.host if http_request.client else "Unknown"
    user_agent = http_request.headers.get("user-agent", "Unknown")
    audit_service.record(
        db=db,
        action="SUPPORT_SESSION_REVOKED",
        entity_type="ORGANIZATION",
        entity_id=session.organization_id,
        actor_user_id=current_user.id,
        organization_id=session.organization_id,
        support_session_id=session.id,
        ip_address=client_ip,
        user_agent=user_agent
    )

    return {"success": True, "message": "Support session revoked"}


@router.get("/support/sessions", response_model=List[SupportSessionOut])
def list_support_sessions(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_permission("PLATFORM_SUPPORT"))
):
    """Lists recent support and impersonation sessions."""
    sessions = db.query(SupportSession).order_by(SupportSession.started_at.desc()).limit(limit).all()
    results = []
    for s in sessions:
        results.append(
            SupportSessionOut(
                id=s.id,
                created_by=s.created_by,
                actor_name=s.actor.full_name if s.actor else "Unknown",
                target_user_id=s.target_user_id,
                target_user_name=s.target_user.full_name if s.target_user else None,
                organization_id=s.organization_id,
                organization_name=s.organization.name if s.organization else "Unknown",
                reason=s.reason,
                started_at=s.started_at,
                expires_at=s.expires_at,
                revoked_at=s.revoked_at,
                is_active=s.is_active,
                support_token=None
            )
        )
    return results
