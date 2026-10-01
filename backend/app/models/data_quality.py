from sqlalchemy import Column, String, Integer, ForeignKey, JSON
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid

class DataQualityJob(Base, TimestampMixin):
    __tablename__ = "data_quality_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="COMPLETED") # RUNNING, COMPLETED, FAILED
    issues_found = Column(Integer, default=0)

class DataQualityIssue(Base, TimestampMixin):
    __tablename__ = "data_quality_issues"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("data_quality_jobs.id", ondelete="CASCADE"), nullable=True)
    
    entity_type = Column(String(50), nullable=False) # LEAD, CONTACT, COMPANY
    entity_id = Column(String(36), nullable=False)
    issue_type = Column(String(50), nullable=False) # INVALID_PHONE, INVALID_EMAIL, MISSING_REQUIRED_FIELD, STALE_RECORD
    severity = Column(String(20), nullable=False, default="WARNING") # CRITICAL, WARNING, INFO
    
    details_json = Column(JSON, nullable=False, default=dict)
    status = Column(String(30), nullable=False, default="OPEN") # OPEN, RESOLVED, IGNORED
    resolved_by = Column(String(36), ForeignKey("users.id"), nullable=True)

class DataQualityResolution(Base, TimestampMixin):
    __tablename__ = "data_quality_resolutions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    issue_id = Column(String(36), ForeignKey("data_quality_issues.id", ondelete="CASCADE"), nullable=False, index=True)
    applied_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    action_taken = Column(String(50), nullable=False) # UPDATED, DELETED, IGNORED
    previous_data = Column(JSON, nullable=False, default=dict)
    new_data = Column(JSON, nullable=False, default=dict)
