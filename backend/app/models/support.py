from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid, utc_now


def default_support_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=15)


class SupportSession(Base, TimestampMixin):
    """
    Explicit Support & Impersonation Session (Problems #19, #20, #46).
    Super Admin never enters tenant context via unverified headers.
    Instead, creates an audited, short-lived (default 15 minutes) signed session.
    """
    __tablename__ = "support_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(String(500), nullable=False)
    started_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, default=default_support_expiry, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Relationships
    actor = relationship("User", foreign_keys=[created_by])
    target_user = relationship("User", foreign_keys=[target_user_id])
    organization = relationship("Organization")

    @property
    def is_active(self) -> bool:
        now = datetime.now(timezone.utc)
        if self.revoked_at is not None:
            return False
        expiry = self.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return now < expiry
