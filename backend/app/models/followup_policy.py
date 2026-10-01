from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class FollowupPolicy(Base):
    __tablename__ = "followup_policies"

    id = Column(String(36), primary_key=True, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    # E.g., "NO_ANSWER_POLICY", "HIGH_INTEREST_POLICY"
    name = Column(String(100), nullable=False)
    trigger_outcome = Column(String(50), nullable=False) # The call outcome that triggers this policy (e.g., "NO_ANSWER")
    
    max_attempts = Column(Integer, default=3)
    interval_minutes = Column(Integer, default=1440) # Default to 24 hours
    
    # Whether this policy assigns to a general NBA queue or specific user
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    organization = relationship("Organization")
