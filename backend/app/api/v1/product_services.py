from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.deps import get_db, get_current_user, get_tenant_id
from app.models.user import User
from app.models.product_service import ProductService
from app.models.organization import Organization
from app.schemas.product_service import ProductServiceCreate, ProductServiceUpdate, ProductServiceOut

router = APIRouter(prefix="/product-services", tags=["Products & Services"])


@router.get("/", response_model=List[ProductServiceOut])
def list_product_services(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    query = db.query(ProductService).filter(ProductService.organization_id == tenant_id)
    if active_only:
        query = query.filter(ProductService.is_active == True)
    
    products = query.order_by(desc(ProductService.created_at)).all()
    return products


@router.post("/", response_model=ProductServiceOut, status_code=status.HTTP_201_CREATED)
def create_product_service(
    data: ProductServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    if not (current_user.is_org_admin or current_user.tenant_role in ("ORG_ADMIN", "SALES_MANAGER", "SUPER_ADMIN")):
        raise HTTPException(status_code=403, detail="Only Managers or Admins can manage the product/service catalog")

    db.query(Organization.id).filter(Organization.id == tenant_id).with_for_update().first()
    duplicate_query = db.query(ProductService.id).filter(
        ProductService.organization_id == tenant_id,
        ProductService.name.ilike(data.name.strip()),
    )
    if data.code:
        duplicate_query = duplicate_query.union(
            db.query(ProductService.id).filter(
                ProductService.organization_id == tenant_id,
                ProductService.code.ilike(data.code.strip()),
            )
        )
    if duplicate_query.first():
        raise HTTPException(status_code=409, detail="A Product/Service with this name or code already exists")
        
    product = ProductService(
        organization_id=tenant_id,
        name=data.name.strip(),
        code=data.code.strip() if data.code else None,
        type=data.type.upper(),
        description=data.description,
        price=data.price,
        currency=data.currency.upper(),
        is_active=data.is_active,
        created_by=current_user.id
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/{id}", response_model=ProductServiceOut)
def get_product_service(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    product = db.query(ProductService).filter(
        ProductService.id == id,
        ProductService.organization_id == tenant_id
    ).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product/Service not found")
    return product


@router.patch("/{id}", response_model=ProductServiceOut)
def update_product_service(
    id: str,
    data: ProductServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    if not (current_user.is_org_admin or current_user.tenant_role in ("ORG_ADMIN", "SALES_MANAGER", "SUPER_ADMIN")):
        raise HTTPException(status_code=403, detail="Only Managers or Admins can manage the product/service catalog")

    product = db.query(ProductService).filter(
        ProductService.id == id,
        ProductService.organization_id == tenant_id
    ).first()
    
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product/Service not found")

    if data.name is not None:
        duplicate = db.query(ProductService.id).filter(
            ProductService.organization_id == tenant_id,
            ProductService.id != product.id,
            ProductService.name.ilike(data.name.strip()),
        ).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="A Product/Service with this name already exists")
        product.name = data.name.strip()
    if data.code is not None:
        if data.code and db.query(ProductService.id).filter(
            ProductService.organization_id == tenant_id,
            ProductService.id != product.id,
            ProductService.code.ilike(data.code.strip()),
        ).first():
            raise HTTPException(status_code=409, detail="A Product/Service with this code already exists")
        product.code = data.code.strip() if data.code else None
    if data.type is not None:
        product.type = data.type.upper()
    if data.description is not None:
        product.description = data.description
    if data.price is not None:
        product.price = data.price
    if data.currency is not None:
        product.currency = data.currency.upper()
    if data.is_active is not None:
        product.is_active = data.is_active

    db.commit()
    db.refresh(product)
    return product
