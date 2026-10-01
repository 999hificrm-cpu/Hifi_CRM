from sqlalchemy import Column, String, ForeignKey, Numeric
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid

class DedupeCandidate(Base, TimestampMixin):
    __tablename__ = "dedupe_candidates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    lead_id_a = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    lead_id_b = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    
    match_confidence = Column(Numeric, nullable=True)
    match_basis = Column(String(100), nullable=True) # e.g. "same phone", "fuzzy name+company"
    status = Column(String(20), nullable=False, default="PENDING") # PENDING, MERGED, KEPT_SEPARATE, IGNORED
