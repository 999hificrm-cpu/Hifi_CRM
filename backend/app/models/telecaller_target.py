from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class TelecallerTarget(Base):
    __tablename__ = "telecaller_targets"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", "target_date", name="uq_telecaller_target_org_user_date"),
    )

    id = Column(String(36), primary_key=True, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    target_date = Column(Date, nullable=False, index=True)
    
    # Target Values
    target_calls = Column(Integer, default=0)
    target_connects = Column(Integer, default=0)
    target_talk_time_minutes = Column(Integer, default=0)
    target_qualified_leads = Column(Integer, default=0)
    target_conversions = Column(Integer, default=0)
    target_revenue = Column(Float, default=0.0)
    
    # Achieved Values (Tracked via DB triggers or application logic)
    achieved_calls = Column(Integer, default=0)
    achieved_connects = Column(Integer, default=0)
    achieved_talk_time_minutes = Column(Integer, default=0)
    achieved_qualified_leads = Column(Integer, default=0)
    achieved_conversions = Column(Integer, default=0)
    achieved_revenue = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="targets")
    organization = relationship("Organization")
