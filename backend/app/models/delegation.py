from sqlalchemy import Column, String, DateTime, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class AbsenceDelegation(Base):
    __tablename__ = "absence_delegations"

    id = Column(String(36), primary_key=True, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    # User who is absent
    absent_user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # User who covers their leads/calls
    cover_user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    absent_user = relationship("User", foreign_keys=[absent_user_id])
    cover_user = relationship("User", foreign_keys=[cover_user_id])
