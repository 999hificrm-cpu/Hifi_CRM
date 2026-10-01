from typing import Set, Optional
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, Session
from app.core.database import Base
from app.models.base import TimestampMixin, SoftDeleteMixin, generate_uuid


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    platform_role = Column(String(30), nullable=True)  # SUPER_ADMIN, PLATFORM_ADMIN, BILLING_ADMIN, SUPPORT_ADMIN, DATA_ADMIN, SECURITY_ADMIN, DATA_OPS
    tenant_role = Column(String(30), nullable=True)    # ORG_ADMIN, SALES_MANAGER, SALES_REP, TELECALLER, VIEWER
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    password_hash = Column(String(255), nullable=False)
    status = Column(String(30), nullable=False, default="ACTIVE")  # INVITED, ACTIVE, SUSPENDED, DEACTIVATED
    token_version = Column(Integer, nullable=False, default=1)
    permission_overrides = Column(JSON, nullable=False, default=dict)
    last_login_at = Column(DateTime, nullable=True)
    gmail_tokens = Column(JSON, nullable=True)  # {"access_token": "...", "refresh_token": "...", "expires_at": ..., "email": "..."}
    telecaller_targets = Column(JSON, nullable=True) # {"calls": 50, "connects": 20, "conversions": 2}

    # Relationships
    organization = relationship("Organization", back_populates="users")
    assigned_leads = relationship("Lead", back_populates="owner", foreign_keys="Lead.owner_id")
    platform_user_roles = relationship("PlatformUserRole", foreign_keys="PlatformUserRole.user_id", back_populates="user", cascade="all, delete-orphan")

    @property
    def is_super_admin(self) -> bool:
        return self.platform_role == "SUPER_ADMIN"

    @property
    def is_data_entry(self) -> bool:
        return self.platform_role in ("DATA_ENTRY", "DATA_OPS", "DATA_ADMIN") or self.tenant_role == "DATA_ENTRY"

    @property
    def is_org_admin(self) -> bool:
        return self.tenant_role == "ORG_ADMIN" or self.is_super_admin

    @property
    def effective_role(self) -> str:
        return self.platform_role or self.tenant_role or "VIEWER"

    def get_effective_platform_permissions(self, db: Optional[Session] = None) -> Set[str]:
        """Resolves all platform permissions from explicit role hierarchy and individual permission overrides."""
        from app.models.rbac import ROLE_PERMISSION_MAP

        perms: Set[str] = set()
        # Direct platform_role column fallback for instant bootstrap
        if self.platform_role and self.platform_role in ROLE_PERMISSION_MAP:
            perms.update(ROLE_PERMISSION_MAP[self.platform_role])

        # DB-backed platform_user_roles mappings if session is provided
        if db:
            from app.models.rbac import PlatformUserRole, PlatformRole, RolePermission, Permission
            user_roles = db.query(PlatformRole).join(
                PlatformUserRole, PlatformUserRole.role_id == PlatformRole.id
            ).filter(PlatformUserRole.user_id == self.id).all()
            for role in user_roles:
                for p in role.permissions:
                    perms.add(p.code)

        # Apply user specific overrides: {"PLATFORM_EXPORT": True, "PLATFORM_ORG_SUSPEND": False}
        if self.permission_overrides and isinstance(self.permission_overrides, dict):
            for p_code, allowed in self.permission_overrides.items():
                if allowed:
                    perms.add(p_code)
                elif p_code in perms:
                    perms.remove(p_code)

        return perms

    def has_platform_permission(self, permission_code: str, db: Optional[Session] = None) -> bool:
        if self.is_super_admin:
            return True
        return permission_code in self.get_effective_platform_permissions(db=db)

