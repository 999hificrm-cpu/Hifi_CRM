from typing import List, Dict, Optional
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Table, UniqueConstraint
from sqlalchemy.orm import relationship, Session
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid, utc_now

# Explicit System Platform Permissions as specified in Master Solution List Problem #16 & #17
PLATFORM_PERMISSIONS = [
    # Organizations
    {"code": "PLATFORM_ORG_READ", "name": "View Organizations", "category": "ORGANIZATIONS", "description": "View all organizations and details"},
    {"code": "PLATFORM_ORG_CREATE", "name": "Create Organizations", "category": "ORGANIZATIONS", "description": "Provision new tenant organizations"},
    {"code": "PLATFORM_ORG_SUSPEND", "name": "Suspend Organizations", "category": "ORGANIZATIONS", "description": "Suspend, deactivate or offboard organizations"},
    # Users
    {"code": "PLATFORM_USER_READ", "name": "View Users", "category": "USERS", "description": "View all platform and tenant users"},
    {"code": "PLATFORM_USER_SUSPEND", "name": "Suspend Users", "category": "USERS", "description": "Suspend or deactivate user accounts"},
    # Billing
    {"code": "PLATFORM_BILLING_READ", "name": "View Billing", "category": "BILLING", "description": "View subscriptions, plans and invoices"},
    {"code": "PLATFORM_BILLING_WRITE", "name": "Manage Billing", "category": "BILLING", "description": "Modify subscriptions, refunds and plan assignments"},
    # Data & Global Registry
    {"code": "PLATFORM_DATA_READ", "name": "View Global Data", "category": "DATA", "description": "View global companies and people directory"},
    {"code": "PLATFORM_DATA_WRITE", "name": "Modify Global Data", "category": "DATA", "description": "Edit and verify global registry entries"},
    {"code": "PLATFORM_EXPORT", "name": "Platform Export", "category": "DATA", "description": "Export tenant or platform datasets"},
    # Security & Audit
    {"code": "PLATFORM_AUDIT_READ", "name": "View Audit Trail", "category": "SECURITY", "description": "View tamper-evident audit logs and security events"},
    # Support & Impersonation
    {"code": "PLATFORM_SUPPORT", "name": "Support Access", "category": "SUPPORT", "description": "Create short-lived audited support sessions"},
    {"code": "PLATFORM_IMPERSONATE", "name": "Impersonate User", "category": "SUPPORT", "description": "Impersonate tenant users under support sessions"},
]

# Role Hierarchies as specified in Problem #17
ROLE_PERMISSION_MAP: Dict[str, List[str]] = {
    "SUPER_ADMIN": [
        "PLATFORM_ORG_READ", "PLATFORM_ORG_CREATE", "PLATFORM_ORG_SUSPEND",
        "PLATFORM_USER_READ", "PLATFORM_USER_SUSPEND",
        "PLATFORM_BILLING_READ", "PLATFORM_BILLING_WRITE",
        "PLATFORM_DATA_READ", "PLATFORM_DATA_WRITE", "PLATFORM_EXPORT",
        "PLATFORM_AUDIT_READ",
        "PLATFORM_SUPPORT", "PLATFORM_IMPERSONATE"
    ],
    "PLATFORM_ADMIN": [
        "PLATFORM_ORG_READ", "PLATFORM_ORG_CREATE", "PLATFORM_ORG_SUSPEND",
        "PLATFORM_USER_READ", "PLATFORM_USER_SUSPEND",
        "PLATFORM_DATA_READ", "PLATFORM_DATA_WRITE", "PLATFORM_EXPORT",
        "PLATFORM_AUDIT_READ", "PLATFORM_SUPPORT"
    ],
    "BILLING_ADMIN": [
        "PLATFORM_ORG_READ",
        "PLATFORM_BILLING_READ", "PLATFORM_BILLING_WRITE",
        "PLATFORM_AUDIT_READ"
    ],
    "SUPPORT_ADMIN": [
        "PLATFORM_ORG_READ", "PLATFORM_USER_READ",
        "PLATFORM_DATA_READ",
        "PLATFORM_SUPPORT", "PLATFORM_IMPERSONATE"
    ],
    "DATA_ADMIN": [
        "PLATFORM_DATA_READ", "PLATFORM_DATA_WRITE", "PLATFORM_EXPORT"
    ],
    "SECURITY_ADMIN": [
        "PLATFORM_AUDIT_READ", "PLATFORM_USER_READ", "PLATFORM_USER_SUSPEND"
    ]
}


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    description = Column(String(255), nullable=True)

    roles = relationship("PlatformRole", secondary="role_permissions", back_populates="permissions")


class PlatformRole(Base, TimestampMixin):
    __tablename__ = "platform_roles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    is_system = Column(Boolean, default=True, nullable=False)

    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")
    user_roles = relationship("PlatformUserRole", back_populates="role", cascade="all, delete-orphan")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)

    id = Column(String(36), primary_key=True, default=generate_uuid)
    role_id = Column(String(36), ForeignKey("platform_roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(String(36), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)


class PlatformUserRole(Base, TimestampMixin):
    __tablename__ = "platform_user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_platform_role"),)

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(String(36), ForeignKey("platform_roles.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at = Column(DateTime, default=utc_now, nullable=False)

    role = relationship("PlatformRole", back_populates="user_roles")
    user = relationship("User", foreign_keys=[user_id], back_populates="platform_user_roles")


def seed_platform_rbac(db: Session) -> None:
    """Idempotently seeds platform permissions and default system roles with their permission maps."""
    # 1. Seed Permissions
    existing_perms = {p.code: p for p in db.query(Permission).all()}
    for perm_data in PLATFORM_PERMISSIONS:
        if perm_data["code"] not in existing_perms:
            p = Permission(
                code=perm_data["code"],
                name=perm_data["name"],
                category=perm_data["category"],
                description=perm_data.get("description", "")
            )
            db.add(p)
            existing_perms[perm_data["code"]] = p
    db.flush()

    # 2. Seed Roles and Role Permissions
    existing_roles = {r.code: r for r in db.query(PlatformRole).all()}
    for role_code, perm_codes in ROLE_PERMISSION_MAP.items():
        role = existing_roles.get(role_code)
        if not role:
            role = PlatformRole(
                code=role_code,
                name=role_code.replace("_", " ").title(),
                description=f"Standard platform role for {role_code.replace('_', ' ').lower()}",
                is_system=True
            )
            db.add(role)
            db.flush()
            existing_roles[role_code] = role

        # Reconcile permissions
        current_perm_ids = {rp.permission_id for rp in db.query(RolePermission).filter(RolePermission.role_id == role.id).all()}
        for pcode in perm_codes:
            perm_obj = existing_perms.get(pcode)
            if perm_obj and perm_obj.id not in current_perm_ids:
                rp = RolePermission(role_id=role.id, permission_id=perm_obj.id)
                db.add(rp)
    db.commit()
