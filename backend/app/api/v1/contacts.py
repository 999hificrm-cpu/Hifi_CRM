from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user, get_tenant_id
from app.models.user import User
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactUpdate, ContactOut
from app.services.contact_service import create_contact, serialize_contact

router = APIRouter(prefix="/contacts", tags=["Contacts"])


@router.get("/", response_model=List[ContactOut])
def list_contacts(
    search: Optional[str] = None,
    company_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    query = db.query(Contact).filter(Contact.organization_id == tenant_id)
    if company_id:
        query = query.filter(Contact.company_id == company_id)
    if search:
        s = f"%{search}%"
        query = query.filter(
            (Contact.full_name.ilike(s)) |
            (Contact.email.ilike(s)) |
            (Contact.phone.ilike(s)) |
            (Contact.designation.ilike(s))
        )
    contacts = query.order_by(Contact.full_name.asc()).offset(skip).limit(limit).all()
    return [serialize_contact(c, current_user, db) for c in contacts]


@router.post("/", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def create_new_contact(
    data: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    contact = create_contact(db, tenant_id, data, current_user.id)
    return serialize_contact(contact, current_user, db)


@router.get("/{id}", response_model=ContactOut)
def get_contact_detail(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    contact = db.query(Contact).filter(
        Contact.id == id,
        Contact.organization_id == tenant_id
    ).first()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return serialize_contact(contact, current_user, db)
