from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from app.core.database import Base
from app.models.base import generate_uuid, utc_now

class GlobalEditRequest(Base):
    __tablename__ = "global_edit_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_type = Column(String(30), nullable=False) # COMPANY or PERSON
    entity_id = Column(String(36), nullable=False, index=True)
    requested_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    changes_json = Column(JSON, nullable=False)
    status = Column(String(30), nullable=False, default="PENDING") # PENDING, APPROVED, REJECTED
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
