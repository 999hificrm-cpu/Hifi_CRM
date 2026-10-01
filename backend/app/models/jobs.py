from sqlalchemy import Column, String, DateTime, Integer, Text
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid, utc_now

class JobRun(Base, TimestampMixin):
    """Tracks every celery task execution for observability"""
    __tablename__ = "job_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(100), index=True, nullable=False) # Celery task ID
    job_type = Column(String(100), index=True, nullable=False) # Task name
    
    status = Column(String(30), nullable=False, default="STARTED") # STARTED, SUCCESS, FAILED, RETRY
    attempt = Column(Integer, nullable=False, default=1)
    
    started_at = Column(DateTime, nullable=False, default=utc_now)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
