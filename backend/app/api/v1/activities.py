from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user, get_tenant_id
from app.models.user import User
from app.schemas.activity import ActivityCreate, ActivityOut
from app.services.activity_service import create_activity, list_activities

router = APIRouter(prefix="/activities", tags=["Activities & Communications"])


@router.post("/", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
def log_activity(
    data: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    return create_activity(db, tenant_id, current_user, data)


@router.get("/", response_model=List[ActivityOut])
def get_activities(
    user_id: Optional[str] = None,
    activity_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    if current_user.tenant_role == "TELECALLER":
        user_id = current_user.id
    return list_activities(db, tenant_id, user_id, activity_type, skip, limit)
