from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FollowupPolicyBase(BaseModel):
    name: str
    trigger_outcome: str
    max_attempts: int = 3
    interval_minutes: int = 1440
    is_active: bool = True

class FollowupPolicyCreate(FollowupPolicyBase):
    pass

class FollowupPolicyUpdate(BaseModel):
    name: Optional[str] = None
    trigger_outcome: Optional[str] = None
    max_attempts: Optional[int] = None
    interval_minutes: Optional[int] = None
    is_active: Optional[bool] = None

class FollowupPolicyOut(FollowupPolicyBase):
    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
