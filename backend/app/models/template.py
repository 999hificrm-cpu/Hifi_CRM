from sqlalchemy import Column, String, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid

class TemplateMedium(str, enum.Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"

class Template(Base, TimestampMixin):
    __tablename__ = "templates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    medium = Column(String(50), nullable=False, default="EMAIL") # EMAIL, SMS, WHATSAPP
    subject = Column(String(255), nullable=True)
    body_template = Column(Text, nullable=False)

    # Relationships
    organization = relationship("Organization")
