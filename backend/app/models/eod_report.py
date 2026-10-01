from sqlalchemy import Column, String, DateTime, ForeignKey, Date, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class EODReport(Base):
    __tablename__ = "eod_reports"

    id = Column(String(36), primary_key=True, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    report_date = Column(Date, nullable=False)
    
    # Store aggregated metrics for the day
    metrics_snapshot = Column(JSON, nullable=False)
    
    # AI generated summary based on metrics
    ai_summary = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User")
