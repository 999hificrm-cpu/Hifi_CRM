from sqlalchemy import Column, String, Boolean, Integer, Numeric, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, SoftDeleteMixin, generate_uuid, utc_now


class Organization(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "organizations"


    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(String(30), nullable=False, default="ACTIVE")  # ACTIVE, SUSPENDED, CANCELLED
    timezone = Column(String(100), nullable=False, default="Asia/Kolkata")
    currency = Column(String(10), nullable=False, default="INR")
    schema_name = Column(String(100), nullable=True, index=True)
    settings = Column(JSON, nullable=False, default=dict)
    feature_overrides = Column(JSON, nullable=True)

    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="organization", cascade="all, delete-orphan")
    companies = relationship("Company", back_populates="organization", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="organization", cascade="all, delete-orphan")
    pipelines = relationship("Pipeline", back_populates="organization", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="organization", cascade="all, delete-orphan")


class Plan(Base, TimestampMixin):
    __tablename__ = "plans"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, nullable=False, index=True)  # STARTER, GROWTH, ENTERPRISE
    name = Column(String(150), nullable=False)
    seat_limit = Column(Integer, nullable=False, default=5)
    monthly_pull_quota = Column(Integer, nullable=False, default=1000)
    price_amount = Column(Numeric(12, 2), nullable=True, default=0.00)
    price_currency = Column(String(10), nullable=False, default="INR")
    feature_flags = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)

    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(String(36), ForeignKey("plans.id"), nullable=False)
    status = Column(String(30), nullable=False, default="ACTIVE")  # TRIALING, ACTIVE, PAST_DUE, CANCELLED
    seats_purchased = Column(Integer, nullable=False, default=5)
    pull_quota_monthly = Column(Integer, nullable=False, default=1000)
    pull_quota_used = Column(Integer, nullable=False, default=0)
    current_period_start = Column(Date, nullable=True)
    current_period_end = Column(Date, nullable=True)
    billing_provider = Column(String(50), nullable=False, default="MANUAL")
    billing_reference = Column(String(255), nullable=True)

    organization = relationship("Organization", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
