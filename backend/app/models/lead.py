from sqlalchemy import Column, String, Integer, Numeric, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, SoftDeleteMixin, generate_uuid


class Lead(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    pipeline_stage_id = Column(String(36), ForeignKey("pipeline_stages.id"), nullable=False, index=True)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    product_service_id = Column(String(36), ForeignKey("product_services.id", ondelete="SET NULL"), nullable=True, index=True)

    title = Column(String(255), nullable=False, index=True)

    # Fast operational snapshots for direct display, calling, filtering, and export controls
    company_name = Column(String(255), nullable=True, index=True)
    contact_name = Column(String(255), nullable=True, index=True)
    contact_email = Column(String(255), nullable=True, index=True)
    contact_phone = Column(String(50), nullable=True, index=True)
    product_service_name = Column(String(255), nullable=True)
    purpose = Column(Text, nullable=True)

    source = Column(String(50), nullable=False, default="MANUAL")  # MANUAL, IMPORT, GLOBAL_PULL, WEBHOOK
    source_global_company_id = Column(String(36), nullable=True)
    source_global_contact_id = Column(String(36), nullable=True)

    lead_type = Column(String(50), nullable=True)  # e.g., INBOUND, OUTBOUND, RENEWAL
    segment = Column(String(10), nullable=True)  # e.g., B2B, B2C

    status = Column(String(30), nullable=False, default="OPEN", index=True)  # OPEN, WON, LOST, ARCHIVED
    priority = Column(String(30), nullable=False, default="MEDIUM")          # LOW, MEDIUM, HIGH, URGENT
    score = Column(Integer, nullable=False, default=50)                       # 0-100 Radar Opportunity Score
    value = Column(Numeric(15, 2), nullable=True, default=0.00)
    currency = Column(String(10), nullable=False, default="INR")
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=False, default=list)

    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="leads")
    company = relationship("Company", back_populates="leads")
    contact = relationship("Contact", back_populates="leads")
    stage = relationship("PipelineStage", back_populates="leads")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="assigned_leads")
    stage_history = relationship("LeadStageHistory", back_populates="lead", cascade="all, delete-orphan", order_by="desc(LeadStageHistory.created_at)")
    activities = relationship("Activity", back_populates="lead", cascade="all, delete-orphan", order_by="desc(Activity.occurred_at)")
    tasks = relationship("Task", back_populates="lead", cascade="all, delete-orphan")
