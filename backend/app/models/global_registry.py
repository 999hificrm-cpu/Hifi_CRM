from sqlalchemy import Column, String, Date, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class GlobalCompany(Base):
    __tablename__ = "global_companies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    registry_country = Column(String(10), nullable=False, default="IN")
    registry_type = Column(String(30), nullable=False, default="CIN")
    registry_id = Column(String(64), nullable=False, unique=True, index=True)  # CIN / Registration number

    legal_name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    company_type = Column(String(50), nullable=True)
    industry = Column(String(150), nullable=True, index=True)
    cin = Column(String(64), nullable=True, index=True)
    registration_number = Column(String(64), nullable=True)
    gst_number = Column(String(64), nullable=True, index=True)
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=False, default="India")
    postal_code = Column(String(20), nullable=True)
    website = Column(String(500), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    status = Column(String(30), nullable=False, default="ACTIVE")  # ACTIVE, DEACTIVATED

    first_seen_at = Column(DateTime, default=utc_now, nullable=False)
    last_updated_at = Column(DateTime, default=utc_now, nullable=False)
    metadata_json = Column(JSON, nullable=False, default=dict)

    pull_status = Column(String(30), nullable=True) # e.g. PULLED
    pulled_at = Column(DateTime, nullable=True)
    pulled_by_org_id = Column(String(36), nullable=True, index=True)
    pulled_by_org_name = Column(String(255), nullable=True)

    # Relationships
    contacts = relationship("GlobalCompanyContactMap", back_populates="company", cascade="all, delete-orphan")


class GlobalContact(Base):
    __tablename__ = "global_contacts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    registry_country = Column(String(10), nullable=False, default="IN")
    registry_type = Column(String(30), nullable=False, default="DIN")
    registry_id = Column(String(64), nullable=True, index=True)  # DIN if known

    full_name = Column(String(255), nullable=False, index=True)
    designation = Column(String(150), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    linkedin_url = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    status = Column(String(30), nullable=False, default="ACTIVE")

    first_seen_at = Column(DateTime, default=utc_now, nullable=False)
    last_updated_at = Column(DateTime, default=utc_now, nullable=False)
    metadata_json = Column(JSON, nullable=False, default=dict)

    companies = relationship("GlobalCompanyContactMap", back_populates="contact", cascade="all, delete-orphan")


class GlobalCompanyContactMap(Base):
    __tablename__ = "global_company_contact_map"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    company_id = Column(String(36), ForeignKey("global_companies.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(String(36), ForeignKey("global_contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    designation = Column(String(150), nullable=True)
    appointment_date = Column(Date, nullable=True)
    status = Column(String(30), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, default=utc_now, nullable=False)

    company = relationship("GlobalCompany", back_populates="contacts")
    contact = relationship("GlobalContact", back_populates="companies")



