from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user, get_tenant_id
from app.models.user import User
from app.schemas.radar import RadarOverviewResponse, AuditLogOut
from app.services.radar_service import get_radar_overview, list_audit_logs

router = APIRouter(prefix="/radar", tags=["Lead Intelligence Radar & Audit"])


@router.get("/overview", response_model=RadarOverviewResponse)
def get_radar_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    # Telecallers receive recommendations for their scope
    user_scope = current_user.id if current_user.tenant_role == "TELECALLER" else None
    return get_radar_overview(db, tenant_id, user_scope)


@router.get("/audit-logs", response_model=List[AuditLogOut])
def get_audit_trail(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org_id = None if current_user.is_super_admin else current_user.organization_id
    return list_audit_logs(db, org_id, skip, limit)
