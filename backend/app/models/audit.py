from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Index, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class AuditLog(Base):
    """
    Centralized, immutable audit trail with SHA-256 hash chaining (Problems #22, #23, #24).
    Guarantees insert-only record keeping with dual-identity support context tracking.
    """
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Dual-identity context for Support / Impersonation sessions (Problems #19, #46)
    actor_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    target_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    support_session_id = Column(String(36), ForeignKey("support_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    context_type = Column(String(30), nullable=False, default="PLATFORM_CONTEXT", index=True)  # PLATFORM_CONTEXT, TENANT_CONTEXT, SUPPORT_CONTEXT
    reason = Column(String(500), nullable=True)

    action = Column(String(100), nullable=False, index=True)  # e.g. ORGANIZATION_SUSPENDED, ROLE_ASSIGNED, LEAD_RESTORED
    entity_type = Column(String(100), nullable=False, index=True)  # LEAD, COMPANY, CONTACT, PIPELINE, USER, ORGANIZATION, ROLE, PERMISSION
    entity_id = Column(String(36), nullable=True, index=True)

    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Cryptographic SHA-256 Tamper-Evident Hash Chaining (Problem #24)
    sequence_number = Column(Integer, nullable=True, index=True)
    event_hash = Column(String(64), nullable=True, index=True)
    previous_event_hash = Column(String(64), nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)


    __table_args__ = (
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_org_created", "organization_id", "created_at"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
        Index("ix_audit_logs_entity_type_id", "entity_type", "entity_id"),
    )



class RadarEvent(Base):
    __tablename__ = "radar_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)  # CONTACT_VIEW, BULK_VIEW, EXPORT_ATTEMPT, MASKED_CALL, REVEAL_REQUEST
    entity_type = Column(String(50), nullable=False)          # LEAD, CONTACT, COMPANY
    entity_id = Column(String(36), nullable=False)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    occurred_at = Column(DateTime, default=utc_now, nullable=False, index=True)
