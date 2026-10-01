from sqlalchemy import Column, String, Integer, DateTime, JSON, Index
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class IdempotencyRecord(Base):
    """
    Stores processed idempotency keys to ensure network retries of consequential
    mutations (e.g. organization suspension, bulk operations, payments) return
    the exact same result without duplicate side-effects.
    """
    __tablename__ = "idempotency_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    key = Column(String(128), unique=True, nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    request_hash = Column(String(64), nullable=False)
    response_status = Column(Integer, nullable=False)
    response_body = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    __table_args__ = (
        Index("ix_idempotency_user_action", "user_id", "action"),
    )
