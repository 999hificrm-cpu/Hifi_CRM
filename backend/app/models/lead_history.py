from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class LeadStageHistory(Base):
    __tablename__ = "lead_stage_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    from_stage_id = Column(String(36), ForeignKey("pipeline_stages.id"), nullable=True)
    to_stage_id = Column(String(36), ForeignKey("pipeline_stages.id"), nullable=False)
    changed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    # Relationships
    lead = relationship("Lead", back_populates="stage_history")
    from_stage = relationship("PipelineStage", foreign_keys=[from_stage_id])
    to_stage = relationship("PipelineStage", foreign_keys=[to_stage_id])
    user = relationship("User", foreign_keys=[changed_by])


class LeadAssignment(Base):
    __tablename__ = "lead_assignments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    assigned_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    is_primary = Column(Boolean, nullable=False, default=True)
    assigned_at = Column(DateTime, default=utc_now, nullable=False)
    unassigned_at = Column(DateTime, nullable=True)

    lead = relationship("Lead")
    user = relationship("User", foreign_keys=[user_id])
