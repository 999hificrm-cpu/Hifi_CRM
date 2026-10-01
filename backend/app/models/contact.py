from sqlalchemy import Column, String, ForeignKey, JSON, Index, text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, SoftDeleteMixin, generate_uuid


class Contact(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "contacts"
    __table_args__ = (
        Index(
            "uq_contact_global_projection",
            "organization_id",
            "source_global_contact_id",
            unique=True,
            postgresql_where=text("source_global_contact_id IS NOT NULL"),
            sqlite_where=text("source_global_contact_id IS NOT NULL"),
        ),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    source_global_contact_id = Column(String(36), nullable=True, index=True)  # Lineage provenance

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    full_name = Column(String(255), nullable=False, index=True)
    designation = Column(String(150), nullable=True)  # e.g., Director, Procurement Head, VP Sales
    department = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    alternate_phone = Column(String(50), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=False, default="India")
    status = Column(String(30), nullable=False, default="ACTIVE")  # ACTIVE, INACTIVE
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    custom_fields = Column(JSON, nullable=False, default=dict)

    # Relationships
    organization = relationship("Organization", back_populates="contacts")
    company = relationship("Company", back_populates="contacts")
    leads = relationship("Lead", back_populates="contact")
