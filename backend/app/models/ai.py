from sqlalchemy import Column, String, Integer, Numeric, Text, DateTime, ForeignKey, JSON
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class AIRun(Base):
    __tablename__ = "ai_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    run_type = Column(String(100), nullable=False, index=True)  # LEAD_SCORE, SUMMARY, NEXT_BEST_ACTION, EMAIL_DRAFT
    entity_type = Column(String(50), nullable=True)              # LEAD, COMPANY, CONTACT
    entity_id = Column(String(36), nullable=True)

    model = Column(String(100), nullable=False, default="jarvis-lead-intelligence-v1")
    input_data = Column(JSON, nullable=False, default=dict)
    output_data = Column(JSON, nullable=False, default=dict)
    tokens_used = Column(Integer, nullable=True, default=0)
    latency_ms = Column(Integer, nullable=True, default=0)
    status = Column(String(30), nullable=False, default="COMPLETED")  # COMPLETED, FAILED
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class AIInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)  # LEAD, COMPANY
    entity_id = Column(String(36), nullable=False, index=True)

    insight_type = Column(String(100), nullable=False)  # OPPORTUNITY_ALERT, RISK_SIGNAL, NEXT_ACTION, BUYING_INTENT
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    score = Column(Numeric(5, 2), nullable=True)
    confidence = Column(Numeric(5, 2), nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=True)
