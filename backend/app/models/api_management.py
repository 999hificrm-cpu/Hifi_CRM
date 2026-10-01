from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, JSON
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid, utc_now

class ApiKey(Base, TimestampMixin):
    """Stores securely hashed API keys for programmatic access"""
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    
    name = Column(String(100), nullable=False)
    key_prefix = Column(String(10), nullable=False, index=True) # Used for identification e.g. JARVIS_sk_abcd...
    key_hash = Column(String(128), nullable=False) # SHA-256 hash of the full key
    
    scopes = Column(JSON, nullable=False, default=list) # ["leads:read", "leads:write", "contacts:read"]
    
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    
    status = Column(String(30), nullable=False, default="ACTIVE") # ACTIVE, REVOKED, EXPIRED

class ApiUsageEvent(Base, TimestampMixin):
    __tablename__ = "api_usage_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    api_key_id = Column(String(36), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    ip_address = Column(String(50), nullable=True)

class ApiRateLimit(Base, TimestampMixin):
    __tablename__ = "api_rate_limits"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    daily_request_limit = Column(Integer, nullable=False, default=10000)
    requests_today = Column(Integer, nullable=False, default=0)
    last_reset_at = Column(DateTime, nullable=False, default=utc_now)
