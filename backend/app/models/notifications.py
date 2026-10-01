from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid, utc_now

class NotificationRule(Base, TimestampMixin):
    __tablename__ = "notification_rules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    event_type = Column(String(50), nullable=False) # e.g., LEAD_ASSIGNED, MENTIONED, PAYMENT_FAILED
    channels = Column(JSON, nullable=False, default=list) # ["IN_APP", "EMAIL"]
    
    is_active = Column(Boolean, default=True)

class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    event_type = Column(String(50), nullable=False)
    event_key = Column(String(100), nullable=True, index=True) # Used for deduplication (e.g. lead_assigned_1234)
    
    title = Column(String(200), nullable=False)
    body = Column(String(1000), nullable=True)
    action_url = Column(String(500), nullable=True)
    
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)

class NotificationDelivery(Base, TimestampMixin):
    __tablename__ = "notification_deliveries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    notification_id = Column(String(36), ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True)
    
    channel = Column(String(20), nullable=False) # IN_APP, EMAIL, SMS
    status = Column(String(20), nullable=False, default="PENDING") # PENDING, SENT, FAILED
    
    external_id = Column(String(100), nullable=True)
    error_message = Column(String(500), nullable=True)
