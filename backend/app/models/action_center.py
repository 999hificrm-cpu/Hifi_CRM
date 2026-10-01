from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid, utc_now

class AdminAlert(Base, TimestampMixin):
    __tablename__ = "admin_alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    alert_type = Column(String(50), nullable=False) # PAYMENT_FAILURE, IMPORT_FAILED, INTEGRATION_FAILED, EXCESSIVE_API_USAGE
    severity = Column(String(20), nullable=False, default="WARNING") # CRITICAL, WARNING, INFO
    
    title = Column(String(200), nullable=False)
    message = Column(String(1000), nullable=True)
    
    status = Column(String(30), nullable=False, default="ACTIVE") # ACTIVE, RESOLVED, DISMISSED
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

class AdminActionItem(Base, TimestampMixin):
    __tablename__ = "admin_action_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    item_type = Column(String(50), nullable=False) # RENEW_SUBSCRIPTION, REVIEW_DEDUPE, REAUTH_INTEGRATION
    priority = Column(String(20), nullable=False, default="MEDIUM") # HIGH, MEDIUM, LOW
    
    title = Column(String(200), nullable=False)
    action_url = Column(String(500), nullable=True)
    
    status = Column(String(30), nullable=False, default="PENDING") # PENDING, COMPLETED, IGNORED
