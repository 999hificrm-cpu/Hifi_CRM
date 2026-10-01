from sqlalchemy import Column, String, Float, DateTime, Text, JSON, ForeignKey
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class GlobalPerson(Base):
    __tablename__ = "global_people"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    full_name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    designation = Column(String(150), nullable=True, index=True)  # Job Title / Role
    company_name = Column(String(255), nullable=True, index=True)
    industry = Column(String(150), nullable=True, index=True)
    seniority = Column(String(50), nullable=True, index=True)  # C-Level, VP, Director, Manager, Lead, Individual Contributor
    department = Column(String(100), nullable=True, index=True)  # Sales, Marketing, Engineering, Operations, Finance, HR, Executive
    linkedin_url = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=False, default="India")
    estimated_value = Column(Float, nullable=False, default=0.0)  # Estimated Deal Value / Budget in INR
    status = Column(String(30), nullable=False, default="ACTIVE")  # ACTIVE, CONTACTED, ARCHIVED
    source = Column(String(50), nullable=False, default="MANUAL")  # MANUAL, IMPORT, DIRECTORY
    notes = Column(Text, nullable=True)
    associated_companies = Column(JSON, nullable=False, default=list)  # [{"company_name": "...", "designation": "..."}]
    metadata_json = Column(JSON, nullable=False, default=dict)

    pull_status = Column(String(30), nullable=True) # e.g. PULLED
    pulled_at = Column(DateTime, nullable=True)
    pulled_by_org_id = Column(String(36), nullable=True, index=True)
    pulled_by_org_name = Column(String(255), nullable=True)

    first_seen_at = Column(DateTime, default=utc_now, nullable=False)
    last_updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
