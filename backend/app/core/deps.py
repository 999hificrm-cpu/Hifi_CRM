import hashlib
from typing import Generator, Optional, Callable, Set
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.organization import Organization, Subscription
from app.models.revocation import RevokedToken
from app.models.support import SupportSession
from app.models.lead import Lead

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def ensure_lead_access(db: Session, lead: Lead, current_user: User, tenant_id: str) -> Lead:
    """Enforce object-level lead access independently of frontend/list filtering."""
    if lead.organization_id != tenant_id or lead.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if current_user.tenant_role != "TELECALLER":
        return lead

    if lead.owner_id == current_user.id:
        return lead

    from app.core.business_time import organization_business_date
    from app.models.delegation import AbsenceDelegation

    business_date = organization_business_date(db, tenant_id)
    delegated = db.query(AbsenceDelegation.id).filter(
        AbsenceDelegation.organization_id == tenant_id,
        AbsenceDelegation.absent_user_id == lead.owner_id,
        AbsenceDelegation.cover_user_id == current_user.id,
        AbsenceDelegation.start_date <= business_date,
        AbsenceDelegation.end_date >= business_date,
    ).first()
    if not delegated:
        # Use a non-enumerating response for records outside a telecaller's scope.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


class RequestContext:
    """
    Explicit Execution Context (Problems #20, #21, #46).
    Distinguishes PLATFORM_CONTEXT, TENANT_CONTEXT, and SUPPORT_CONTEXT.
    """
    def __init__(
        self,
        context_type: str,
        actor_user: User,
        acting_as_user: Optional[User] = None,
        organization_id: Optional[str] = None,
        support_session_id: Optional[str] = None
    ):
        self.context_type = context_type  # PLATFORM_CONTEXT, TENANT_CONTEXT, SUPPORT_CONTEXT
        self.actor_user = actor_user
        self.acting_as_user = acting_as_user
        self.organization_id = organization_id
        self.support_session_id = support_session_id

    @property
    def is_support(self) -> bool:
        return self.context_type == "SUPPORT_CONTEXT"


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Authenticates user from JWT and verifies token_version and revocation table
    (Problems #15, #18, #20).
    """
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Fast RevokedToken blacklist check
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    if db.query(RevokedToken).filter(RevokedToken.token_hash == token_hash).first():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been explicitly revoked. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # 2. Soft-deletion check (Problem #10, #42)
    if getattr(user, "is_deleted", False) or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated or removed"
        )

    if user.status in ("SUSPENDED", "DEACTIVATED"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive or suspended")

    # 3. Token Version check for immediate mass revocation (Problems #15, #18)
    token_ver = payload.get("token_version")
    if token_ver is not None and user.token_version is not None:
        if token_ver != user.token_version:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked or invalidated. Please sign in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 4. If token is a Support Session token, validate the session is still active (Problem #19, #46)
    if payload.get("type") == "support_session":
        session_id = payload.get("support_session_id")
        session = db.query(SupportSession).filter(SupportSession.id == session_id).first()
        if not session or not session.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Support session has expired or was revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return user


def get_request_context(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user)
) -> RequestContext:
    """
    Resolves the active execution context:
    - SUPPORT_CONTEXT: If authenticated with a short-lived support token
    - TENANT_CONTEXT: If normal tenant user operating within their organization
    - PLATFORM_CONTEXT: If platform staff operating globally
    """
    payload = decode_access_token(token) or {}
    if payload.get("type") == "support_session":
        actor_id = payload.get("actor_user_id")
        actor_user = db.query(User).filter(User.id == actor_id).first() or current_user
        target_id = payload.get("target_user_id")
        target_user = db.query(User).filter(User.id == target_id).first() if target_id else None
        return RequestContext(
            context_type="SUPPORT_CONTEXT",
            actor_user=actor_user,
            acting_as_user=target_user,
            organization_id=payload.get("organization_id"),
            support_session_id=payload.get("support_session_id")
        )

    if current_user.organization_id:
        return RequestContext(
            context_type="TENANT_CONTEXT",
            actor_user=current_user,
            organization_id=current_user.organization_id
        )

    return RequestContext(
        context_type="PLATFORM_CONTEXT",
        actor_user=current_user
    )


def require_platform_permission(permission_code: str) -> Callable:
    """
    Fine-grained Platform RBAC Dependency (Problems #16, #17, #18).
    Enforces that the authenticated user possesses the specific platform permission.
    """
    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        if current_user.is_super_admin:
            return current_user

        if not current_user.has_platform_permission(permission_code, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Platform permission '{permission_code}' required"
            )
        return current_user

    return dependency


def require_super_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin platform privilege required"
        )
    return current_user


def require_platform_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not (current_user.platform_role in ("SUPER_ADMIN", "PLATFORM_ADMIN", "DATA_OPS", "DATA_ADMIN", "SECURITY_ADMIN", "SUPPORT_ADMIN", "BILLING_ADMIN")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform staff access required"
        )
    return current_user


def require_org_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_org_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization Admin privilege required"
        )
    return current_user


def get_tenant_id(
    current_user: User = Depends(get_current_user),
    x_tenant_id: Optional[str] = Header(None),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> str:
    """
    Resolves the active tenant ID (Problems #20, #21, #46):
    - In SUPPORT_CONTEXT: strictly extracted from the cryptographically signed support token payload.
    - For normal tenant users: ALWAYS current_user.organization_id.
    - For Super Admin with explicit header: permitted with validation that organization exists and is active.
    Sets PostgreSQL search_path to the tenant's isolated schema.
    """
    payload = decode_access_token(token) or {}
    tenant_id: Optional[str] = None

    if payload.get("type") == "support_session" and payload.get("organization_id"):
        tenant_id = payload["organization_id"]
    elif current_user.organization_id:
        tenant_id = current_user.organization_id
    elif current_user.is_super_admin or (current_user.platform_role and current_user.platform_role.startswith("PLATFORM_")):
        if x_tenant_id:
            # Validate tenant exists and is not soft deleted
            org = db.query(Organization).filter(Organization.id == x_tenant_id).first()
            if not org or org.is_deleted:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant organization not found")
            tenant_id = x_tenant_id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Platform user must specify tenant context via Support Session or X-Tenant-Id header"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any tenant organization"
        )

    # Enforce Subscription Access (Phase 3 Billing)
    if tenant_id:
        sub = db.query(Subscription).filter(Subscription.organization_id == tenant_id).first()
        if sub:
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).date()
            
            # Transition to EXPIRED if trial or active period has passed
            if sub.status in ("TRIALING", "ACTIVE", "GRACE_PERIOD") and sub.current_period_end and sub.current_period_end < today:
                sub.status = "EXPIRED"
                db.commit()
                db.refresh(sub)
                
            if sub.status in ("EXPIRED", "SUSPENDED", "CANCELLED"):
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Organization subscription is inactive or trial has expired. Please contact support or upgrade."
                )

    # Route PostgreSQL search_path to tenant's isolated schema
    if db.bind and db.bind.dialect.name == "postgresql":
        try:
            org = db.query(Organization).filter(Organization.id == tenant_id).first()
            if org and org.schema_name:
                db.tenant_schema = org.schema_name
                db.execute(text(f'SET search_path TO "{org.schema_name}", public'))
        except Exception:
            pass

    return tenant_id


def get_optional_tenant_id(
    current_user: User = Depends(get_current_user),
    x_tenant_id: Optional[str] = Header(None),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[str]:
    payload = decode_access_token(token) or {}
    tenant_id: Optional[str] = None

    if payload.get("type") == "support_session" and payload.get("organization_id"):
        tenant_id = payload["organization_id"]
    elif current_user.organization_id:
        tenant_id = current_user.organization_id
    elif current_user.is_super_admin:
        tenant_id = x_tenant_id

    # Route PostgreSQL search_path to tenant's isolated schema if tenant_id is resolved
    if tenant_id and db.bind and db.bind.dialect.name == "postgresql":
        try:
            org = db.query(Organization).filter(Organization.id == tenant_id).first()
            if org and org.schema_name:
                db.tenant_schema = org.schema_name
                db.execute(text(f'SET search_path TO "{org.schema_name}", public'))
        except Exception:
            pass

    return tenant_id
