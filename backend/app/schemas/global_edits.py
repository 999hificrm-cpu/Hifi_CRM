from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class GlobalEditRequestCreate(BaseModel):
    entity_type: str  # "COMPANY" or "PERSON"
    entity_id: str
    changes_json: Dict[str, Any]

class GlobalEditRequestOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    requested_by: str
    changes_json: Dict[str, Any]
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

    class Config:
        from_attributes = True

class GlobalEditResolveRequest(BaseModel):
    status: str  # "APPROVED" or "REJECTED"
