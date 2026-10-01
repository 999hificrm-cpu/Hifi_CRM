from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class ContactPhone(Base, TimestampMixin):
    __tablename__ = "contact_phones"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    phone_number = Column(String(50), nullable=False, index=True)  # Normalized E.164
    phone_type = Column(String(20), nullable=False, default="UNKNOWN")  # MOBILE, LANDLINE, WHATSAPP, UNKNOWN, INVALID
    label = Column(String(50), nullable=True)  # Primary, Alternate, Work
    
    is_primary = Column(Boolean, nullable=False, default=False)
    is_whatsapp = Column(Boolean, nullable=False, default=False)
    is_sms_capable = Column(Boolean, nullable=False, default=False)
    is_callable = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    
    country_code = Column(String(5), nullable=True)

    # Relationships
    contact = relationship("Contact", backref="phones")
