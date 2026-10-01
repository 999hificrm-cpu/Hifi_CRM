from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.deps import require_super_admin, require_platform_permission
from app.models.user import User
from app.models.organization import Organization
from app.models.lead import Lead
from app.models.company import Company
from app.models.contact import Contact
from app.services.audit_service import audit_service

router = APIRouter(prefix="/admin/recovery", tags=["Admin Recovery & Recycle Bin"])

ENTITY_MODEL_MAP = {
    "leads": Lead,
    "users": User,
    "organizations": Organization,
    "companies": Company,
    "contacts": Contact
}


class RecoverableItemOut(BaseModel):
    id: str
    entity_type: str
    display_name: str
    organization_id: Optional[str] = None
    deleted_at: datetime
    deleted_by: Optional[str] = None
    deletion_reason: Optional[str] = None


class RestoreRequest(BaseModel):
    reason: Optional[str] = "Restored by platform administrator"


@router.get("/{entity}", response_model=List[RecoverableItemOut])
def list_deleted_items(
    entity: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_permission("PLATFORM_DATA_READ"))
):
    """
    Lists soft-deleted items from the Recycle Bin (Problems #10, #41, #42).
    """
    model = ENTITY_MODEL_MAP.get(entity.lower())
    if not model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity type '{entity}'. Supported: {list(ENTITY_MODEL_MAP.keys())}"
        )

    offset = (page - 1) * page_size
    query = db.query(model).filter(model.deleted_at.isnot(None)).order_by(desc(model.deleted_at))
    items = query.offset(offset).limit(page_size).all()

    results = []
    for item in items:
        # Resolve a friendly display name based on model attributes
        display_name = getattr(item, "name", None) or getattr(item, "title", None) or getattr(item, "full_name", None) or getattr(item, "email", str(item.id))
        org_id = getattr(item, "organization_id", None)
        results.append(
            RecoverableItemOut(
                id=item.id,
                entity_type=entity.upper()[:-1] if entity.endswith("s") else entity.upper(),
                display_name=display_name,
                organization_id=org_id,
                deleted_at=item.deleted_at,
                deleted_by=item.deleted_by,
                deletion_reason=item.deletion_reason
            )
        )
    return results


@router.post("/{entity}/{item_id}/restore")
def restore_item(
    entity: str,
    item_id: str,
    req: RestoreRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_permission("PLATFORM_DATA_WRITE"))
):
    """
    Restores a soft-deleted entity from the Recycle Bin (Problem #10).
    """
    model = ENTITY_MODEL_MAP.get(entity.lower())
    if not model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity type")

    item = db.query(model).filter(model.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    if not item.deleted_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item is not deleted")

    old_vals = {
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
        "deleted_by": item.deleted_by,
        "deletion_reason": item.deletion_reason
    }

    item.deleted_at = None
    item.deleted_by = None
    item.deletion_reason = None
    db.commit()

    client_ip = http_request.client.host if http_request.client else "Unknown"
    user_agent = http_request.headers.get("user-agent", "Unknown")
    audit_service.record(
        db=db,
        action=f"{entity.upper()[:-1]}_RESTORED",
        entity_type=entity.upper()[:-1],
        entity_id=item.id,
        actor_user_id=current_user.id,
        organization_id=getattr(item, "organization_id", None),
        old_values=old_vals,
        new_values={"status": "RESTORED"},
        reason=req.reason,
        ip_address=client_ip,
        user_agent=user_agent
    )

    return {"success": True, "message": f"Successfully restored {entity[:-1]} {item.id}"}


@router.delete("/{entity}/{item_id}/purge")
def permanently_purge_item(
    entity: str,
    item_id: str,
    reason: str = Query(..., min_length=5, description="Mandatory reason for permanent purge"),
    http_request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Permanently purges an item from the database.
    Strictly guarded: requires Super Admin privileges and mandatory justification (Problems #10, #41).
    """
    model = ENTITY_MODEL_MAP.get(entity.lower())
    if not model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity type")

    item = db.query(model).filter(model.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    org_id = getattr(item, "organization_id", None)
    display_name = getattr(item, "name", None) or getattr(item, "title", None) or getattr(item, "email", str(item.id))

    db.delete(item)
    db.commit()

    client_ip = http_request.client.host if (http_request and http_request.client) else "Unknown"
    user_agent = http_request.headers.get("user-agent", "Unknown") if http_request else "Unknown"
    audit_service.record(
        db=db,
        action=f"{entity.upper()[:-1]}_PURGED",
        entity_type=entity.upper()[:-1],
        entity_id=item_id,
        actor_user_id=current_user.id,
        organization_id=org_id,
        old_values={"display_name": display_name},
        new_values={"purged": True},
        reason=reason,
        ip_address=client_ip,
        user_agent=user_agent
    )

    return {"success": True, "message": f"Permanently purged {entity[:-1]} {item_id}"}
