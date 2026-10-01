from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.global_edits import GlobalEditRequest
from app.models.global_registry import GlobalCompany
from app.models.global_people import GlobalPerson
from app.schemas.global_edits import GlobalEditRequestCreate, GlobalEditRequestOut, GlobalEditResolveRequest
from app.models.base import generate_uuid

router = APIRouter(prefix="/global-edits", tags=["Global Intelligence Edits"])

@router.post("/", response_model=GlobalEditRequestOut, status_code=status.HTTP_201_CREATED)
def submit_edit_request(
    data: GlobalEditRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_data_entry:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Data Entry users should submit edit requests here."
        )

    # Validate entity exists
    if data.entity_type == "COMPANY":
        ent = db.query(GlobalCompany).filter(GlobalCompany.id == data.entity_id).first()
    elif data.entity_type == "PERSON":
        ent = db.query(GlobalPerson).filter(GlobalPerson.id == data.entity_id).first()
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity type")

    if not ent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    edit_req = GlobalEditRequest(
        id=generate_uuid(),
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        requested_by=current_user.id,
        changes_json=data.changes_json,
        status="PENDING"
    )
    db.add(edit_req)
    db.commit()
    db.refresh(edit_req)
    return edit_req


@router.get("/admin", response_model=List[GlobalEditRequestOut])
def list_pending_edits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin privilege required to view pending edits"
        )
    
    edits = db.query(GlobalEditRequest).filter(GlobalEditRequest.status == "PENDING").order_by(GlobalEditRequest.created_at.asc()).all()
    return edits


@router.post("/{id}/resolve", response_model=GlobalEditRequestOut)
def resolve_edit_request(
    id: str,
    data: GlobalEditResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin privilege required to resolve edits"
        )
    
    edit_req = db.query(GlobalEditRequest).filter(GlobalEditRequest.id == id).first()
    if not edit_req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edit request not found")

    if edit_req.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request already resolved")

    if data.status not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid resolution status")

    edit_req.status = data.status
    edit_req.resolved_at = datetime.now(timezone.utc)
    edit_req.resolved_by = current_user.id

    if data.status == "APPROVED":
        # Apply the changes
        if edit_req.entity_type == "COMPANY":
            ent = db.query(GlobalCompany).filter(GlobalCompany.id == edit_req.entity_id).first()
            if ent:
                for k, v in edit_req.changes_json.items():
                    if hasattr(ent, k):
                        setattr(ent, k, v)
        elif edit_req.entity_type == "PERSON":
            ent = db.query(GlobalPerson).filter(GlobalPerson.id == edit_req.entity_id).first()
            if ent:
                for k, v in edit_req.changes_json.items():
                    if hasattr(ent, k):
                        setattr(ent, k, v)

    db.commit()
    db.refresh(edit_req)
    return edit_req
