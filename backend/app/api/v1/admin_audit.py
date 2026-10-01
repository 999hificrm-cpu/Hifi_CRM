from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.core.deps import require_platform_permission
from app.models.user import User
from app.models.audit import AuditLog
from app.services.audit_service import audit_service

router = APIRouter(prefix="/admin", tags=["Admin Audit"])


class AuditLogOut(BaseModel):
    id: str
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    actor_user_id: Optional[str] = None
    target_user_id: Optional[str] = None
    support_session_id: Optional[str] = None
    context_type: str
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    reason: Optional[str] = None
    event_hash: Optional[str] = None
    previous_event_hash: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogPageOut(BaseModel):
    items: List[AuditLogOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class ChainVerificationResult(BaseModel):
    status: str
    is_valid: bool = True
    verified_count: int
    latest_event_hash: Optional[str] = None
    tampered_at_id: Optional[str] = None
    index: Optional[int] = None
    message: str


@router.get("/audit-logs", response_model=AuditLogPageOut)
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    context_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_permission("PLATFORM_AUDIT_READ"))
):
    """
    Paginated, indexed audit logs query (Problems #22, #23).
    Allows fine-grained filtering without loading large datasets into browser memory.
    """
    query = db.query(AuditLog)

    if action and action != "ALL":
        query = query.filter(AuditLog.action == action)
    if entity_type and entity_type != "ALL":
        query = query.filter(AuditLog.entity_type == entity_type)
    if actor_user_id:
        query = query.filter((AuditLog.actor_user_id == actor_user_id) | (AuditLog.user_id == actor_user_id))
    if organization_id and organization_id != "ALL":
        query = query.filter(AuditLog.organization_id == organization_id)
    if context_type and context_type != "ALL":
        query = query.filter(AuditLog.context_type == context_type)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return AuditLogPageOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/audit-logs/verify-chain", response_model=ChainVerificationResult)
def verify_audit_log_chain(
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_permission("PLATFORM_AUDIT_READ"))
):
    """
    Cryptographic verification endpoint (Problem #24).
    Validates SHA-256 hash chains across the audit record sequence to guarantee tamper-resistance.
    """
    res = audit_service.verify_chain(db=db, limit=limit)
    res["is_valid"] = (res.get("status") == "VALID")
    return ChainVerificationResult(**res)
