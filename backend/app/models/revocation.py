from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid, utc_now


class RevokedToken(Base, TimestampMixin):
    """
    Tracks explicitly revoked JWT tokens (by token jti or sha256 hash)
    for immediate session invalidation before natural expiry.
    """
    __tablename__ = "revoked_tokens"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    revoked_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    reason = Column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_revoked_tokens_hash_expires", "token_hash", "expires_at"),
    )
