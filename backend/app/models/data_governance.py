from sqlalchemy import Column, String, ForeignKey, JSON, DateTime
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid, utc_now

class GlobalDataChangeRequest(Base, TimestampMixin):
    __tablename__ = "global_data_change_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    global_entity_type = Column(String(50), nullable=False) # COMPANY, PERSON
    global_entity_id = Column(String(36), nullable=False)
    
    requested_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    
    proposed_changes = Column(JSON, nullable=False, default=dict)
    reason = Column(String(500), nullable=True)
    
    status = Column(String(30), nullable=False, default="PENDING_REVIEW") # DRAFT, PENDING_REVIEW, APPROVED, REJECTED, APPLIED
    
    reviewed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(String(500), nullable=True)
