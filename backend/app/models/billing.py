from sqlalchemy import Column, String, Numeric, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class BillingEvent(Base, TimestampMixin):
    __tablename__ = "billing_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    provider = Column(String(50), nullable=False) # e.g., 'generic', 'stripe', 'razorpay'
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    processed_status = Column(String(30), nullable=False, default="PENDING") # PENDING, PROCESSED, FAILED

    organization = relationship("Organization")


class PaymentTransaction(Base, TimestampMixin):
    __tablename__ = "payment_transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    status = Column(String(30), nullable=False, default="PENDING") # PENDING, SUCCESS, FAILED
    provider_reference = Column(String(255), nullable=True)

    organization = relationship("Organization")
    subscription = relationship("Subscription")
