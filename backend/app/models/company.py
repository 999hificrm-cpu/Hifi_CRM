from sqlalchemy import Column, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, SoftDeleteMixin, generate_uuid


class Company(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    source_global_company_id = Column(String(36), nullable=True, index=True)  # Lineage provenance

    name = Column(String(255), nullable=False, index=True)
    legal_name = Column(String(255), nullable=True)
    domain = Column(String(255), nullable=True, index=True)
    cin = Column(String(64), nullable=True, index=True)
    gstin = Column(String(64), nullable=True)
    industry = Column(String(150), nullable=True, index=True)
    company_size = Column(String(50), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=False, default="India")
    postal_code = Column(String(20), nullable=True)
    status = Column(String(30), nullable=False, default="ACTIVE")  # ACTIVE, ARCHIVED
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    custom_fields = Column(JSON, nullable=False, default=dict)

    # Relationships
    organization = relationship("Organization", back_populates="companies")
    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="company")
