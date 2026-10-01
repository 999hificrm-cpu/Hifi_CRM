from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal
from datetime import datetime


class ActivityCreate(BaseModel):
    lead_id: Optional[str] = None
    company_id: Optional[str] = None
    contact_id: Optional[str] = None
    activity_type: str  # CALL, WHATSAPP, EMAIL, NOTE, MEETING, STAGE_CHANGE, ASSIGNMENT, TASK
    subject: Optional[str] = None
    description: Optional[str] = None
    direction: Optional[str] = "OUTBOUND"
    status: Optional[str] = "COMPLETED"  # CONNECTED, NO_ANSWER, BUSY, SCHEDULED, FAILED
    duration_seconds: Optional[int] = 0
    metadata_json: Optional[Dict[str, Any]] = None
    # A call outcome and a pipeline stage are separate business facts.  The
    # Desk sends the selected stage so both can be persisted atomically.
    pipeline_stage_id: Optional[str] = None
    # Follow-ups are explicit.  Omitting the field never infers a callback
    # from the outcome or a legacy policy.
    followup_preset: Optional[Literal["tomorrow", "3days", "nextweek", "none"]] = None


class ActivityOut(BaseModel):
    id: str
    organization_id: str
    lead_id: Optional[str] = None
    company_id: Optional[str] = None
    contact_id: Optional[str] = None
    user_id: str
    user_name: Optional[str] = None
    activity_type: str
    subject: Optional[str] = None
    description: Optional[str] = None
    direction: Optional[str] = None
    status: str
    duration_seconds: Optional[int] = 0
    metadata_json: Dict[str, Any] = {}
    occurred_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
