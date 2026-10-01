from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from app.core.database import Base
from app.models.base import generate_uuid, utc_now

class CommunicationLog(Base):
    __tablename__ = "communication_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=True, index=True)
    
    channel = Column(String(20), nullable=False) # WHATSAPP, EMAIL, SMS
    direction = Column(String(10), nullable=False) # INBOUND, OUTBOUND
    message_id = Column(String(100), nullable=True)
    body = Column(Text, nullable=True)
    
    status = Column(String(20), nullable=False, default="PENDING") # SENT, DELIVERED, READ, FAILED, PENDING
    sent_at = Column(DateTime(timezone=True), default=utc_now)
