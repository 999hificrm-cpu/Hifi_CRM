from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid, utc_now

class Integration(Base, TimestampMixin):
    __tablename__ = "integrations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    provider = Column(String(50), nullable=False) # ZAPIER, EXOTEL, SENDGRID, GOOGLE_ADS
    status = Column(String(30), nullable=False, default="DISCONNECTED") # CONNECTED, DISCONNECTED, ERROR, REAUTH_REQUIRED
    
    config = Column(JSON, nullable=False, default=dict)
    
    last_synced_at = Column(DateTime, nullable=True)
    last_error = Column(String(500), nullable=True)

class IntegrationCredential(Base, TimestampMixin):
    __tablename__ = "integration_credentials"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    integration_id = Column(String(36), ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Store encrypted credentials here - in production, this should use Vault or AWS KMS
    encrypted_payload = Column(String(2000), nullable=False)

class IntegrationEvent(Base, TimestampMixin):
    __tablename__ = "integration_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    integration_id = Column(String(36), ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    event_type = Column(String(50), nullable=False) # WEBHOOK_RECEIVED, SYNC_STARTED, SYNC_FAILED
    status = Column(String(20), nullable=False) # SUCCESS, FAILED
    
    payload = Column(JSON, nullable=True)
    error_message = Column(String(500), nullable=True)
