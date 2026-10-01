from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.deps import get_db, get_current_user, get_tenant_id
from app.models.user import User
from app.models.api_management import ApiKey
from app.services.api_service import create_api_key

router = APIRouter(prefix="/api-keys", tags=["API Keys"])

class ApiKeyCreate(BaseModel):
    name: str
    scopes: List[str] = []
    expires_in_days: Optional[int] = 365

class ApiKeyOut(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: List[str]
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    status: str
    created_at: datetime

class ApiKeyCreateResponse(ApiKeyOut):
    raw_key: str # Only returned once

@router.post("/", response_model=ApiKeyCreateResponse)
def create_key(
    data: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    if not current_user.is_org_admin:
        raise HTTPException(status_code=403, detail="Only Org Admins can manage API keys")
        
    raw_key = create_api_key(db, tenant_id, data.name, current_user.id, data.scopes, data.expires_in_days)
    
    # We fetch the created key from db to serialize it
    key_prefix = raw_key[:16]
    api_key = db.query(ApiKey).filter(ApiKey.key_prefix == key_prefix).first()
    
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key_prefix": api_key.key_prefix,
        "scopes": api_key.scopes,
        "expires_at": api_key.expires_at,
        "last_used_at": api_key.last_used_at,
        "status": api_key.status,
        "created_at": api_key.created_at,
        "raw_key": raw_key # SECURITY: This is the ONLY time this is shown
    }

@router.get("/", response_model=List[ApiKeyOut])
def list_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    if not current_user.is_org_admin:
        raise HTTPException(status_code=403, detail="Only Org Admins can view API keys")
        
    keys = db.query(ApiKey).filter(ApiKey.organization_id == tenant_id).all()
    return keys

@router.post("/{key_id}/revoke")
def revoke_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    if not current_user.is_org_admin:
        raise HTTPException(status_code=403, detail="Only Org Admins can revoke API keys")
        
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.organization_id == tenant_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key not found")
        
    api_key.status = "REVOKED"
    db.commit()
    return {"status": "success", "message": "API Key revoked"}
