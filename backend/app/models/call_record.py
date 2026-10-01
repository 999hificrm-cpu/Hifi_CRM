from sqlalchemy import Column, String, Integer, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid


class CallRecord(Base):
    __tablename__ = "call_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=True, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    provider = Column(String(30), nullable=True)  # TWILIO, EXOTEL, NATIVE_DIALER
    provider_call_id = Column(String(100), nullable=True)
    direction = Column(String(10), nullable=True)  # INBOUND, OUTBOUND
    
    started_at = Column(DateTime, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True, default=0)
    
    disposition = Column(String(50), nullable=True)  # CONNECTED, NO_ANSWER, BUSY, WRONG_NUMBER, INTERESTED
    
    recording_url = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    sentiment = Column(String(20), nullable=True)
    ai_score = Column(Numeric(5, 2), nullable=True)

    # Relationships
    lead = relationship("Lead", backref="call_records")
    user = relationship("User", backref="call_records")
