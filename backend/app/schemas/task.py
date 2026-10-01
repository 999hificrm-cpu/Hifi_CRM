from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.schemas.lead import LeadOut


class TaskCreate(BaseModel):
    lead_id: Optional[str] = None
    company_id: Optional[str] = None
    contact_id: Optional[str] = None
    task_type: Optional[str] = "FOLLOW_UP"  # FOLLOW_UP, CALL, MEETING, GENERAL
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "MEDIUM"
    due_at: Optional[datetime] = None
    assigned_to: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_to: Optional[str] = None


class TaskRescheduleRequest(BaseModel):
    new_due_at: datetime
    reason: Optional[str] = None


class TaskOut(BaseModel):
    id: str
    organization_id: str
    lead_id: Optional[str] = None
    company_id: Optional[str] = None
    contact_id: Optional[str] = None
    task_type: str
    title: str
    description: Optional[str] = None
    priority: str
    status: str
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    created_by: Optional[str] = None
    reschedule_count: int = 0
    reschedule_history: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FollowupOut(TaskOut):
    """Telecaller follow-up projection backed by one persisted Task row."""

    lead: LeadOut
    display_status: str
    last_outcome: Optional[str] = None
    attempt_count: int = 0
