from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user, get_tenant_id
from app.models.user import User
from app.schemas.global_registry import (
    GlobalCompanyOut,
    GlobalCompanyCreate,
    GlobalCompanyUpdate,
    GlobalPullRequest,
    GlobalPullResponse,
    GlobalIntelligenceResponse
)
from app.services.global_service import (
    search_global_companies,
    create_global_company,
    update_global_company,
    pull_global_companies_to_crm
)
from app.services.global_intelligence_service import get_global_intelligence

router = APIRouter(prefix="/global", tags=["Global Intelligence Registry"])


def _require_registry_read(user: User) -> None:
    if not (user.is_org_admin or user.is_super_admin or user.is_data_entry):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Global Registry access requires Organization Admin or platform data privileges")


@router.get("/intelligence", response_model=GlobalIntelligenceResponse)
def get_intelligence(
    search: Optional[str] = None,
    filter_type: Optional[str] = "ALL",
    city: Optional[str] = None,
    industry: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_registry_read(current_user)
    return get_global_intelligence(
        db=db,
        search=search,
        filter_type=filter_type,
        city=city,
        industry=industry,
        skip=skip,
        limit=limit,
        current_user=current_user
    )


@router.get("/companies", response_model=List[GlobalCompanyOut])
def get_global_companies(
    search: Optional[str] = None,
    city: Optional[str] = None,
    industry: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_registry_read(current_user)
    return search_global_companies(db, search, city, industry, skip, limit, current_user=current_user)


@router.post("/companies", response_model=GlobalCompanyOut, status_code=status.HTTP_201_CREATED)
def create_company(
    data: GlobalCompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not (current_user.is_super_admin or current_user.is_data_entry):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Data Entry privilege required to add companies"
        )
    return create_global_company(db, data)


@router.put("/companies/{id}", response_model=GlobalCompanyOut)
def edit_company(
    id: str,
    data: GlobalCompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not (current_user.is_super_admin or current_user.is_data_entry):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin or Data Entry privilege required to edit companies"
        )
    return update_global_company(db, id, data)


@router.post("/pull", response_model=GlobalPullResponse)
def pull_companies_to_crm(
    data: GlobalPullRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    if current_user.is_super_admin or current_user.is_data_entry:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform users (Super Admin / Data Entry) cannot pull leads directly. Leads can only be pulled into CRM organizations by Organization Admins."
        )
    if not current_user.is_org_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization Admin privilege required to pull companies into CRM")
    return pull_global_companies_to_crm(
        db=db,
        organization_id=tenant_id,
        user=current_user,
        global_company_ids=data.global_company_ids,
        target_stage_id=data.target_stage_id,
        target_owner_id=data.target_owner_id
    )
