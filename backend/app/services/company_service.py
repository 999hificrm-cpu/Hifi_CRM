from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.company import Company
from app.models.audit import AuditLog
from app.schemas.company import CompanyCreate, CompanyUpdate


def create_company(db: Session, organization_id: str, data: CompanyCreate, user_id: str = None) -> Company:
    # Check domain duplicate if provided
    if data.domain:
        existing = db.query(Company).filter(
            Company.organization_id == organization_id,
            Company.domain == data.domain.lower().strip()
        ).first()
        if existing:
            return existing

    company = Company(
        organization_id=organization_id,
        name=data.name.strip(),
        legal_name=data.legal_name.strip() if data.legal_name else data.name.strip(),
        domain=data.domain.lower().strip() if data.domain else None,
        cin=data.cin.strip().upper() if data.cin else None,
        gstin=data.gstin.strip().upper() if data.gstin else None,
        industry=data.industry,
        company_size=data.company_size,
        phone=data.phone,
        email=data.email.lower().strip() if data.email else None,
        website=data.website,
        address=data.address,
        city=data.city,
        state=data.state,
        country=data.country or "India",
        postal_code=data.postal_code,
        created_by=user_id,
        custom_fields=data.custom_fields or {}
    )
    db.add(company)
    db.flush()

    audit = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        action="COMPANY_CREATED",
        entity_type="COMPANY",
        entity_id=company.id,
        new_values={"name": company.name, "domain": company.domain}
    )
    db.add(audit)
    db.commit()
    try:
        db.refresh(company)
    except Exception:
        pass
    return company


def get_or_create_company(
    db: Session,
    organization_id: str,
    name: str,
    domain: Optional[str] = None,
    cin: Optional[str] = None,
    city: Optional[str] = None,
    user_id: Optional[str] = None
) -> Tuple[Company, bool]:
    """
    Finds existing company by CIN, domain, or normalized name within organization,
    or creates a new one. Returns (company, created).
    """
    clean_name = name.strip()
    clean_domain = domain.lower().strip() if domain else None
    clean_cin = cin.strip().upper() if cin else None

    # Priority 1: Check CIN
    if clean_cin:
        company = db.query(Company).filter(
            Company.organization_id == organization_id,
            Company.cin == clean_cin
        ).first()
        if company:
            return company, False

    # Priority 2: Check Domain
    if clean_domain:
        company = db.query(Company).filter(
            Company.organization_id == organization_id,
            Company.domain == clean_domain
        ).first()
        if company:
            return company, False

    # Priority 3: Check Name match
    company = db.query(Company).filter(
        Company.organization_id == organization_id,
        Company.name.ilike(clean_name)
    ).first()
    if company:
        return company, False

    # Create new company
    new_company = Company(
        organization_id=organization_id,
        name=clean_name,
        legal_name=clean_name,
        domain=clean_domain,
        cin=clean_cin,
        city=city,
        created_by=user_id
    )
    db.add(new_company)
    db.flush()
    return new_company, True


def list_companies(
    db: Session,
    organization_id: str,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
) -> List[Company]:
    query = db.query(Company).filter(Company.organization_id == organization_id)
    if search:
        s = f"%{search}%"
        query = query.filter(
            (Company.name.ilike(s)) |
            (Company.domain.ilike(s)) |
            (Company.city.ilike(s)) |
            (Company.industry.ilike(s))
        )
    return query.order_by(Company.name.asc()).offset(skip).limit(limit).all()


def get_company(db: Session, company_id: str, organization_id: str) -> Company:
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.organization_id == organization_id
    ).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company
