from sqlalchemy import Column, String, DateTime, ForeignKey
from app.core.database import Base
from app.models.base import generate_uuid, utc_now

class AvailabilityStatus(Base):
    __tablename__ = "availability_status"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False) # AVAILABLE, ON_BREAK, OFFLINE, ABSENT, LEAVE, SUSPENDED
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False)
    reason = Column(String(255), nullable=True)
    approved_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
