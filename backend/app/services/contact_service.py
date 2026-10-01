from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.contact import Contact
from app.models.audit import AuditLog
from app.models.contact_phone import ContactPhone
from app.models.user import User
from app.schemas.contact import ContactCreate, ContactUpdate, ContactOut
from app.services.masking_service import should_mask_field, mask_phone_number, mask_email_address


def create_contact(db: Session, organization_id: str, data: ContactCreate, user_id: str = None) -> Contact:
    from app.services.telephony_service import parse_and_format_phone
    phone_norm, p_type, p_sms = parse_and_format_phone(data.phone)
    contact = Contact(
        organization_id=organization_id,
        company_id=data.company_id,
        first_name=data.first_name,
        last_name=data.last_name,
        full_name=data.full_name.strip(),
        designation=data.designation,
        department=data.department,
        email=data.email.lower().strip() if data.email else None,
        phone=phone_norm if phone_norm else data.phone,
        alternate_phone=data.alternate_phone,
        linkedin_url=data.linkedin_url,
        city=data.city,
        state=data.state,
        country=data.country or "India",
        created_by=user_id,
        custom_fields=data.custom_fields or {}
    )
    db.add(contact)
    db.flush()

    if phone_norm:
        cp = ContactPhone(
            contact_id=contact.id,
            phone_number=phone_norm,
            phone_type=p_type,
            label="Primary",
            is_primary=True,
            is_sms_capable=p_sms,
            is_callable=True
        )
        db.add(cp)

    audit = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        action="CONTACT_CREATED",
        entity_type="CONTACT",
        entity_id=contact.id,
        new_values={"full_name": contact.full_name, "email": contact.email}
    )
    db.add(audit)
    db.commit()
    try:
        db.refresh(contact)
    except Exception:
        pass
    return contact


def get_or_create_contact(
    db: Session,
    organization_id: str,
    full_name: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    company_id: Optional[str] = None,
    designation: Optional[str] = None,
    user_id: Optional[str] = None
) -> Tuple[Contact, bool]:
    clean_name = full_name.strip()
    from app.services.telephony_service import parse_and_format_phone
    clean_phone, p_type, p_sms = parse_and_format_phone(phone)
    clean_email = email.lower().strip() if email else None

    # Priority 1: Check phone match within org
    if clean_phone:
        contact = db.query(Contact).filter(
            Contact.organization_id == organization_id,
            Contact.phone == clean_phone
        ).first()
        if contact:
            return contact, False

    # Priority 2: Check email match within org
    if clean_email:
        contact = db.query(Contact).filter(
            Contact.organization_id == organization_id,
            Contact.email == clean_email
        ).first()
        if contact:
            return contact, False

    # Priority 3: Check full name + company match
    if company_id:
        contact = db.query(Contact).filter(
            Contact.organization_id == organization_id,
            Contact.company_id == company_id,
            Contact.full_name.ilike(clean_name)
        ).first()
        if contact:
            return contact, False

    # Create new contact
    new_contact = Contact(
        organization_id=organization_id,
        company_id=company_id,
        full_name=clean_name,
        phone=clean_phone if clean_phone else phone,
        email=clean_email,
        designation=designation,
        created_by=user_id
    )
    db.add(new_contact)
    db.flush()
    
    if clean_phone:
        cp = ContactPhone(
            contact_id=new_contact.id,
            phone_number=clean_phone,
            phone_type=p_type,
            label="Primary",
            is_primary=True,
            is_sms_capable=p_sms,
            is_callable=True
        )
        db.add(cp)
        
    return new_contact, True


def serialize_contact(contact: Contact, user: User, db: Session) -> ContactOut:
    mask_phone = should_mask_field(db, contact.organization_id, user, "PHONE")
    mask_email = should_mask_field(db, contact.organization_id, user, "EMAIL")

    phone_val = mask_phone_number(contact.phone) if (mask_phone and contact.phone) else contact.phone
    email_val = mask_email_address(contact.email) if (mask_email and contact.email) else contact.email

    return ContactOut(
        id=contact.id,
        organization_id=contact.organization_id,
        company_id=contact.company_id,
        first_name=contact.first_name,
        last_name=contact.last_name,
        full_name=contact.full_name,
        designation=contact.designation,
        department=contact.department,
        email=email_val,
        phone=phone_val,
        alternate_phone=mask_phone_number(contact.alternate_phone) if (mask_phone and contact.alternate_phone) else contact.alternate_phone,
        linkedin_url=contact.linkedin_url,
        city=contact.city,
        state=contact.state,
        country=contact.country,
        status=contact.status,
        is_phone_masked=mask_phone,
        is_email_masked=mask_email,
        created_at=contact.created_at,
        updated_at=contact.updated_at
    )
