from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, get_optional_tenant_id
from app.models.user import User
from app.schemas.global_people import (
    GlobalPersonCreate,
    GlobalPersonUpdate,
    GlobalPersonOut,
    GlobalPeoplePullRequest,
    GlobalPeoplePullResponse,
)
from app.services.global_people_service import (
    search_global_people,
    create_global_person,
    update_global_person,
    pull_global_people_to_crm,
)

router = APIRouter(prefix="/global/people", tags=["Global People Intelligence"])


@router.get("/", response_model=List[GlobalPersonOut])
def get_global_people(
    search: Optional[str] = None,
    department: Optional[str] = None,
    seniority: Optional[str] = None,
    city: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search and retrieve executive profiles from the Global People Intelligence registry."""
    if not (current_user.is_org_admin or current_user.is_super_admin or current_user.is_data_entry):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Global People access requires Organization Admin or platform data privileges")
    return search_global_people(
        db=db,
        search=search,
        department=department,
        seniority=seniority,
        city=city,
        skip=skip,
        limit=limit,
        current_user=current_user
    )


@router.post("/", response_model=GlobalPersonOut, status_code=status.HTTP_201_CREATED)
def create_person_lead(
    data: GlobalPersonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Single add lead feature with detailed input fields for the People Intelligence registry."""
    if not (current_user.is_super_admin or current_user.is_data_entry):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Data Entry privilege required to add people to the Global Intelligence directory"
        )
    return create_global_person(db=db, data=data)


@router.put("/{id}", response_model=GlobalPersonOut)
def edit_person_lead(
    id: str,
    data: GlobalPersonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update profile and company association in People Intelligence registry."""
    if not (current_user.is_super_admin or current_user.is_data_entry):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin or Data Entry privilege required to edit people intelligence profiles"
        )
    return update_global_person(db=db, person_id=id, data=data)


@router.post("/pull", response_model=GlobalPeoplePullResponse)
def pull_people_to_crm(
    data: GlobalPeoplePullRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: Optional[str] = Depends(get_optional_tenant_id)
):
    """Pull selected people leads into a target tenant organization CRM with full contact & company mapping."""
    if current_user.is_super_admin or current_user.is_data_entry:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform users (Super Admin / Data Entry) cannot pull leads directly. Leads can only be pulled into CRM organizations by Organization Admins."
        )

    if not current_user.is_org_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization Admin privilege required to pull people into CRM",
        )

    # Tenant context comes from the authenticated user. A payload tenant ID is
    # intentionally ignored so it cannot become an IDOR primitive.
    target_org_id = tenant_id
    if not target_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target organization required to pull people leads into CRM"
        )

    return pull_global_people_to_crm(
        db=db,
        organization_id=target_org_id,
        user=current_user,
        global_people_ids=data.global_people_ids,
        target_stage_id=data.target_stage_id,
        target_owner_id=data.target_owner_id
    )
