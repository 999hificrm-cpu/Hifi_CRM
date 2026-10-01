from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class AIScoreRequest(BaseModel):
    lead_id: str


class AIScoreResponse(BaseModel):
    lead_id: str
    score: int
    qualification_tier: str  # HOT, HIGH, MEDIUM, LOW, COLD
    key_signals: List[str]
    conversion_probability: float


class AISummaryResponse(BaseModel):
    lead_id: str
    headline: str
    business_context: str
    key_stakeholders: List[str]
    past_interactions_summary: str
    risk_factors: List[str]
    suggested_next_step: str


class NextBestActionResponse(BaseModel):
    lead_id: str
    recommended_action: str
    channel: str  # CALL, WHATSAPP, EMAIL
    reason: str
    suggested_message: Optional[str] = None
