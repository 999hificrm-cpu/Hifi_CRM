from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.config import settings
from app.models.base import generate_uuid, utc_now


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    job_type = Column(String(50), nullable=False)  # TENANT_LEADS, TENANT_CONTACTS, GLOBAL_COMPANIES, GLOBAL_CONTACTS
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # CSV, XLSX, XLS
    file_path = Column(String(500), nullable=True)

    total_rows = Column(Integer, nullable=False, default=0)
    processed_rows = Column(Integer, nullable=False, default=0)
    successful_rows = Column(Integer, nullable=False, default=0)
    duplicate_rows = Column(Integer, nullable=False, default=0)
    error_rows = Column(Integer, nullable=False, default=0)

    status = Column(String(30), nullable=False, default="PENDING", index=True)  # PENDING, VALIDATING, PROCESSING, COMPLETED, PARTIAL, FAILED
    column_mapping = Column(JSON, nullable=False, default=dict)
    target_stage_id = Column(String(36), ForeignKey("pipeline_stages.id"), nullable=True)
    target_owner_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    default_product_service_id = Column(String(36), ForeignKey("product_services.id", ondelete="SET NULL"), nullable=True)
    error_summary = Column(JSON, nullable=False, default=dict)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    row_errors = relationship("ImportRowError", back_populates="job", cascade="all, delete-orphan")
    uploader = relationship("User", foreign_keys=[uploaded_by])


class ImportRowError(Base):
    __tablename__ = "import_row_errors"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    raw_data = Column(JSON, nullable=False, default=dict)
    error_code = Column(String(100), nullable=False)
    error_message = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    job = relationship("ImportJob", back_populates="row_errors")
