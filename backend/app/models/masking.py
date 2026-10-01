from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid, utc_now


class MaskingPolicy(Base, TimestampMixin):
    __tablename__ = "masking_policies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_role = Column(String(50), nullable=False)  # TELECALLER, SALES_REP, VIEWER
    field = Column(String(50), nullable=False)        # PHONE, EMAIL, ALTERNATE_PHONE
    is_masked = Column(Boolean, nullable=False, default=True)


class MaskingException(Base):
    __tablename__ = "masking_exceptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    field = Column(String(50), nullable=False)
    granted_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    granted_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    reason = Column(Text, nullable=True)
