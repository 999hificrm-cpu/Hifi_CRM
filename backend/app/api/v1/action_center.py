from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.core.deps import get_db, get_current_user, get_tenant_id
from app.models.user import User
from app.models.action_center import AdminAlert, AdminActionItem

router = APIRouter(prefix="/action-center", tags=["Action Center"])

class AdminAlertOut(BaseModel):
    id: str
    alert_type: str
    severity: str
    title: str
    message: str
    status: str
    created_at: datetime

class AdminActionItemOut(BaseModel):
    id: str
    item_type: str
    priority: str
    title: str
    action_url: str
    status: str
    created_at: datetime

@router.get("/alerts", response_model=List[AdminAlertOut])
def get_admin_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    if not current_user.is_org_admin:
        raise HTTPException(status_code=403, detail="Only Org Admins can view Action Center")
        
    alerts = db.query(AdminAlert).filter(
        AdminAlert.organization_id == tenant_id,
        AdminAlert.status == "ACTIVE"
    ).order_by(desc(AdminAlert.created_at)).limit(50).all()
    
    return alerts

@router.get("/items", response_model=List[AdminActionItemOut])
def get_admin_action_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    if not current_user.is_org_admin:
        raise HTTPException(status_code=403, detail="Only Org Admins can view Action Center")
        
    items = db.query(AdminActionItem).filter(
        AdminActionItem.organization_id == tenant_id,
        AdminActionItem.status == "PENDING"
    ).order_by(desc(AdminActionItem.created_at)).limit(50).all()
    
    return items

@router.post("/alerts/{alert_id}/dismiss")
def dismiss_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    if not current_user.is_org_admin:
        raise HTTPException(status_code=403, detail="Only Org Admins can dismiss alerts")
        
    alert = db.query(AdminAlert).filter(AdminAlert.id == alert_id, AdminAlert.organization_id == tenant_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    alert.status = "DISMISSED"
    alert.resolved_by = current_user.id
    db.commit()
    return {"status": "success"}
