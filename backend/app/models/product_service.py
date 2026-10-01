from sqlalchemy import Column, String, Boolean, ForeignKey, Numeric, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.core.database import Base

class ProductService(Base):
    __tablename__ = "product_services"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100), nullable=True)
    type = Column(String(50), nullable=False, default="PRODUCT") # PRODUCT or SERVICE
    description = Column(String(1000), nullable=True)
    price = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), nullable=False, default="INR")
    is_active = Column(Boolean, default=True)
    
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    organization = relationship("Organization")
    creator = relationship("User", foreign_keys=[created_by])
