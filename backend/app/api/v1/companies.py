from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user, get_tenant_id
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyOut
from app.services.company_service import create_company, list_companies, get_company

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get("/", response_model=List[CompanyOut])
def get_companies(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    return list_companies(db, tenant_id, search, skip, limit)


@router.post("/", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_new_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    return create_company(db, tenant_id, data, current_user.id)


@router.get("/{id}", response_model=CompanyOut)
def get_company_detail(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    return get_company(db, id, tenant_id)
