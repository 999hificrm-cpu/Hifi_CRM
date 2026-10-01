import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.global_registry import GlobalCompany, GlobalContact, GlobalCompanyContactMap
from app.models.global_people import GlobalPerson
from app.models.organization import Organization, Subscription
from app.models.company import Company
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.lead_history import LeadStageHistory
from app.models.user import User
from app.schemas.global_registry import GlobalCompanyOut, GlobalCompanyCreate, GlobalCompanyUpdate, GlobalPullResponse
from app.services.pipeline_service import get_first_stage, get_stage_by_id


def search_global_companies(
    db: Session,
    search: Optional[str] = None,
    city: Optional[str] = None,
    industry: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: Optional[User] = None
) -> List[GlobalCompanyOut]:
    query = db.query(GlobalCompany).filter(GlobalCompany.status == "ACTIVE")
    
    tenant_id = getattr(current_user, "organization_id", None)
    pulled_company_ids = set()
    
    if tenant_id:
        pulled_comps = db.query(Company.source_global_company_id).filter(
            Company.organization_id == tenant_id,
            Company.source_global_company_id.isnot(None)
        ).all()
        pulled_company_ids = {c[0] for c in pulled_comps}

    if search:
        s = f"%{search}%"
        query = query.filter(
            (GlobalCompany.legal_name.ilike(s)) |
            (GlobalCompany.registry_id.ilike(s)) |
            (GlobalCompany.display_name.ilike(s)) |
            (GlobalCompany.cin.ilike(s)) |
            (GlobalCompany.gst_number.ilike(s)) |
            (GlobalCompany.registration_number.ilike(s))
        )
    if city:
        query = query.filter(GlobalCompany.city.ilike(f"%{city}%"))
    if industry:
        query = query.filter(GlobalCompany.industry.ilike(f"%{industry}%"))

    companies = query.order_by(GlobalCompany.first_seen_at.desc(), GlobalCompany.legal_name.asc()).offset(skip).limit(limit).all()

    results = []
    for c in companies:
        cnt = db.query(GlobalCompanyContactMap).filter(GlobalCompanyContactMap.company_id == c.id).count()
        results.append(GlobalCompanyOut(
            id=c.id,
            registry_id=c.registry_id,
            legal_name=c.legal_name,
            display_name=c.display_name,
            company_type=c.company_type,
            industry=c.industry,
            cin=c.cin or c.registry_id,
            registration_number=c.registration_number,
            gst_number=c.gst_number,
            address=c.address,
            postal_code=c.postal_code,
            website=c.website,
            email=c.email,
            phone=c.phone,
            city=c.city,
            state=c.state,
            country=c.country,
            status="PULLED" if c.id in pulled_company_ids else c.status,
            contacts_count=cnt,
            first_seen_at=c.first_seen_at,
            last_updated_at=c.last_updated_at
        ))
    return results


def create_global_company(db: Session, data: GlobalCompanyCreate) -> GlobalCompanyOut:
    company_id = data.id.strip() if data.id and data.id.strip() else str(uuid.uuid4())

    # Ensure unique ID
    if db.query(GlobalCompany).filter(GlobalCompany.id == company_id).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company with ID '{company_id}' already exists."
        )

    # Determine registry_id (CIN or registration number or auto-generated)
    registry_id = (data.cin or data.registration_number or f"REG-{uuid.uuid4().hex[:8].upper()}").strip()
    existing_reg = db.query(GlobalCompany).filter(GlobalCompany.registry_id == registry_id).first()
    if existing_reg:
        registry_id = f"{registry_id}-{uuid.uuid4().hex[:4].upper()}"

    company = GlobalCompany(
        id=company_id,
        registry_country="IN",
        registry_type="CIN" if data.cin else "OTHER",
        registry_id=registry_id,
        legal_name=data.legal_name.strip(),
        display_name=data.legal_name.strip(),
        company_type=data.company_type or "Private Limited",
        industry=data.industry.strip() if data.industry else None,
        cin=data.cin.strip() if data.cin else None,
        registration_number=data.registration_number.strip() if data.registration_number else None,
        gst_number=data.gst_number.strip() if data.gst_number else None,
        address=data.address.strip() if data.address else None,
        city=data.city.strip() if data.city else None,
        postal_code=data.postal_code.strip() if data.postal_code else None,
        state=data.state.strip() if data.state else None,
        country=data.country or "India",
        website=data.website.strip() if data.website else None,
        email=data.email.strip() if data.email else None,
        phone=data.phone.strip() if data.phone else None,
        status="ACTIVE"
    )
    db.add(company)
    db.commit()
    try:
        db.refresh(company)
    except Exception:
        pass

    return GlobalCompanyOut(
        id=company.id,
        registry_id=company.registry_id,
        legal_name=company.legal_name,
        display_name=company.display_name,
        company_type=company.company_type,
        industry=company.industry,
        cin=company.cin or company.registry_id,
        registration_number=company.registration_number,
        gst_number=company.gst_number,
        address=company.address,
        postal_code=company.postal_code,
        website=company.website,
        email=company.email,
        phone=company.phone,
        city=company.city,
        state=company.state,
        country=company.country,
        status=company.status,
        contacts_count=0,
        first_seen_at=company.first_seen_at,
        last_updated_at=company.last_updated_at
    )



def pull_global_companies_to_crm(
    db: Session,
    organization_id: str,
    user: User,
    global_company_ids: List[str],
    target_stage_id: Optional[str] = None,
    target_owner_id: Optional[str] = None
) -> GlobalPullResponse:
    # 1. Check active subscription and remaining pull quota
    sub = db.query(Subscription).filter(
        Subscription.organization_id == organization_id,
        Subscription.status == "ACTIVE"
    ).with_for_update().first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription found for this organization"
        )

    # De-duplicate the request before quota validation and claiming.
    global_company_ids = list(dict.fromkeys(global_company_ids))
    # Quota is evaluated against successful *new tenant projections*, not the
    # number of IDs supplied by a client.  This makes retrying an idempotent
    # pull safe and avoids charging for missing/already-projected records.
    remaining_quota = max(0, sub.pull_quota_monthly - sub.pull_quota_used)

    # 2. Resolve target stage
    if target_stage_id:
        stage = get_stage_by_id(db, target_stage_id, organization_id)
    else:
        stage = get_first_stage(db, organization_id)

    if target_owner_id:
        owner = db.query(User).filter(
            User.id == target_owner_id,
            User.organization_id == organization_id,
            User.tenant_role == "TELECALLER",
            User.status == "ACTIVE",
            User.deleted_at.is_(None),
        ).first()
        if not owner:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target owner is not an active telecaller in this organization")

    pulled_comps = 0
    pulled_conts = 0
    created_leads = 0

    org = db.query(Organization).filter(Organization.id == organization_id).first()
    org_name = org.name if org else "Organization"
    now_utc = datetime.now(timezone.utc)

    for g_id in global_company_ids:
        # Lock the master row for the duration of claim + tenant projection.
        # This prevents two concurrent pulls from both consuming the same
        # global record in PostgreSQL.
        g_comp = db.query(GlobalCompany).filter(GlobalCompany.id == g_id).with_for_update().first()
        if not g_comp:
            continue

        # Check if already pulled or existing in tenant CRM
        crm_comp = db.query(Company).filter(
            Company.organization_id == organization_id,
            (Company.source_global_company_id == g_comp.id) | (Company.cin == g_comp.registry_id)
        ).first()

        if not crm_comp:
            if pulled_comps >= remaining_quota:
                # Preserve partial-success semantics without charging a
                # record that cannot be projected within the locked quota.
                continue
            crm_comp = Company(
                organization_id=organization_id,
                source_global_company_id=g_comp.id,
                name=g_comp.legal_name,
                legal_name=g_comp.legal_name,
                cin=g_comp.registry_id,
                industry=g_comp.industry,
                website=g_comp.website,
                email=g_comp.email,
                phone=g_comp.phone,
                city=g_comp.city,
                state=g_comp.state,
                country=g_comp.country,
                created_by=user.id
            )
            db.add(crm_comp)
            db.flush()
            pulled_comps += 1

        # Pull associated contacts
        mapped_contacts = db.query(GlobalCompanyContactMap).filter(
            GlobalCompanyContactMap.company_id == g_comp.id
        ).all()

        primary_contact = None
        for mc in mapped_contacts:
            g_contact = mc.contact
            crm_cont = db.query(Contact).filter(
                Contact.organization_id == organization_id,
                Contact.company_id == crm_comp.id,
                Contact.full_name == g_contact.full_name
            ).first()

            if not crm_cont:
                crm_cont = Contact(
                    organization_id=organization_id,
                    company_id=crm_comp.id,
                    source_global_contact_id=g_contact.id,
                    full_name=g_contact.full_name,
                    designation=mc.designation or g_contact.designation,
                    email=g_contact.email,
                    phone=g_contact.phone,
                    linkedin_url=g_contact.linkedin_url,
                    city=g_contact.city,
                    created_by=user.id
                )
                db.add(crm_cont)
                db.flush()
                pulled_conts += 1

            if not primary_contact:
                primary_contact = crm_cont

        # Create active CRM lead from pulled company
        existing_lead = db.query(Lead).filter(
            Lead.organization_id == organization_id,
            Lead.company_id == crm_comp.id
        ).first()

        if not existing_lead:
            new_lead = Lead(
                organization_id=organization_id,
                company_id=crm_comp.id,
                contact_id=primary_contact.id if primary_contact else None,
                pipeline_stage_id=stage.id,
                owner_id=target_owner_id,
                title=f"{crm_comp.name} - Global Expansion",
                company_name=crm_comp.name,
                contact_name=primary_contact.full_name if primary_contact else None,
                contact_email=primary_contact.email if primary_contact else crm_comp.email,
                contact_phone=primary_contact.phone if primary_contact else crm_comp.phone,
                source="GLOBAL_PULL",
                source_global_company_id=g_comp.id,
                status="OPEN",
                priority="HIGH",
                score=75,
                created_by=user.id
            )
            db.add(new_lead)
            db.flush()

            # Record Stage History
            history = LeadStageHistory(
                organization_id=organization_id,
                lead_id=new_lead.id,
                from_stage_id=None,
                to_stage_id=stage.id,
                changed_by=user.id,
                reason="Pulled from Global Intelligence Registry",
                duration_seconds=0
            )
            db.add(history)
            created_leads += 1

    # 3. Deduct only successful claims (new tenant company projections).
    successful_claim_count = pulled_comps
    if sub.pull_quota_used + successful_claim_count > sub.pull_quota_monthly:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pull quota exhausted")
    sub.pull_quota_used += successful_claim_count
    db.commit()

    return GlobalPullResponse(
        pulled_companies=pulled_comps,
        pulled_contacts=pulled_conts,
        created_leads=created_leads,
        remaining_quota=sub.pull_quota_monthly - sub.pull_quota_used
    )


def update_global_company(db: Session, company_id: str, data: GlobalCompanyUpdate) -> GlobalCompanyOut:
    company = db.query(GlobalCompany).filter(GlobalCompany.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID '{company_id}' not found."
        )

    fields = [
        "legal_name", "cin", "registration_number", "gst_number",
        "address", "city", "postal_code", "state", "website",
        "email", "phone", "country", "industry", "company_type", "status"
    ]
    for field in fields:
        val = getattr(data, field)
        if val is not None:
            setattr(company, field, val.strip() if isinstance(val, str) else val)
            if field == "legal_name" and val:
                company.display_name = val.strip()

    company.last_updated_at = datetime.now(timezone.utc)
    db.commit()
    try:
        db.refresh(company)
    except Exception:
        pass

    cnt = db.query(GlobalCompanyContactMap).filter(GlobalCompanyContactMap.company_id == company.id).count()
    return GlobalCompanyOut(
        id=company.id,
        registry_id=company.registry_id,
        legal_name=company.legal_name,
        display_name=company.display_name,
        company_type=company.company_type,
        industry=company.industry,
        cin=company.cin or company.registry_id,
        registration_number=company.registration_number,
        gst_number=company.gst_number,
        address=company.address,
        postal_code=company.postal_code,
        website=company.website,
        email=company.email,
        phone=company.phone,
        city=company.city,
        state=company.state,
        country=company.country,
        status=company.status,
        contacts_count=cnt,
        first_seen_at=company.first_seen_at,
        last_updated_at=company.last_updated_at
    )
