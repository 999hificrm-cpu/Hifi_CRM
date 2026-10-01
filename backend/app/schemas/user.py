from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime


class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str
    phone: Optional[str] = None
    tenant_role: Optional[str] = "SALES_REP"  # ORG_ADMIN, SALES_MANAGER, SALES_REP, TELECALLER, VIEWER
    platform_role: Optional[str] = None       # SUPER_ADMIN, DATA_OPS (for platform only)
    organization_id: Optional[str] = None
    permission_overrides: Optional[Dict[str, Any]] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    tenant_role: Optional[str] = None
    status: Optional[str] = None
    permission_overrides: Optional[Dict[str, Any]] = None
    telecaller_targets: Optional[Dict[str, Any]] = None


class UserOut(BaseModel):
    id: str
    organization_id: Optional[str] = None
    platform_role: Optional[str] = None
    tenant_role: Optional[str] = None
    full_name: str
    email: str
    phone: Optional[str] = None
    status: str
    permission_overrides: Dict[str, Any] = {}
    telecaller_targets: Optional[Dict[str, Any]] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
