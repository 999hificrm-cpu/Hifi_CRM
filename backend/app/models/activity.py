from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class Activity(Base):
    __tablename__ = "activities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=True, index=True)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    activity_type = Column(String(50), nullable=False, index=True)  # CALL, WHATSAPP, EMAIL, NOTE, MEETING, STAGE_CHANGE, ASSIGNMENT, TASK
    subject = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    direction = Column(String(20), nullable=True, default="OUTBOUND")  # INBOUND, OUTBOUND
    status = Column(String(50), nullable=False, default="COMPLETED")   # COMPLETED, CONNECTED, NO_ANSWER, BUSY, SCHEDULED, FAILED
    duration_seconds = Column(Integer, nullable=True, default=0)
    metadata_json = Column(JSON, nullable=False, default=dict)
    occurred_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    lead = relationship("Lead", back_populates="activities")
    user = relationship("User")
    contact = relationship("Contact")
    company = relationship("Company")
