from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session

from app.core.business_time import followup_preset_due_at
from app.core.deps import get_current_user, get_db, get_tenant_id
from app.models.task import Task
from app.models.user import User
from app.schemas.task import FollowupOut, TaskOut, TaskRescheduleRequest
from app.services.followup_service import (
    active_followup_query,
    followup_attempt_count,
    latest_followup_outcome,
)
from app.services.lead_service import serialize_lead
from app.services.task_service import complete_task, reschedule_task

router = APIRouter(prefix="/followups", tags=["Follow-ups"])


class RescheduleRequest(BaseModel):
    new_due_at: Optional[datetime] = None
    preset: Optional[Literal["tomorrow", "3days", "nextweek"]] = None
    reason: Optional[str] = None

    @model_validator(mode="after")
    def require_one_schedule_choice(self):
        if (self.new_due_at is None) == (self.preset is None):
            raise ValueError("Provide exactly one of new_due_at or preset")
        return self


def _followup_projection(db: Session, task: Task, current_user: User) -> FollowupOut:
    due = task.due_at
    comparable_due = due.replace(tzinfo=timezone.utc) if due and due.tzinfo is None else due
    display_status = "OVERDUE" if comparable_due and comparable_due < datetime.now(timezone.utc) else "PENDING"
    payload = TaskOut.model_validate(task).model_dump()
    payload["assigned_to_name"] = task.assignee.full_name if task.assignee else None
    return FollowupOut(
        **payload,
        lead=serialize_lead(task.lead, current_user, db),
        display_status=display_status,
        last_outcome=latest_followup_outcome(db, task),
        attempt_count=followup_attempt_count(db, task),
    )


@router.get("/", response_model=List[FollowupOut])
def list_followups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """Return only actionable, accessible persisted follow-ups."""
    tasks = active_followup_query(db, tenant_id, current_user).order_by(Task.due_at.asc()).all()
    return [_followup_projection(db, task, current_user) for task in tasks]


@router.post("/{task_id}/complete", response_model=TaskOut)
def complete_followup(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    if not active_followup_query(db, tenant_id, current_user).filter(Task.id == task_id).first():
        raise HTTPException(status_code=404, detail="Follow-up not found")
    return complete_task(db, task_id, tenant_id, current_user)


@router.post("/{task_id}/reschedule", response_model=TaskOut)
def reschedule_followup(
    task_id: str,
    req: RescheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    if not active_followup_query(db, tenant_id, current_user).filter(Task.id == task_id).first():
        raise HTTPException(status_code=404, detail="Follow-up not found")
    due_at = req.new_due_at or followup_preset_due_at(db, tenant_id, req.preset)
    if due_at is None:
        raise HTTPException(status_code=422, detail="A valid future due time is required")
    return reschedule_task(
        db,
        task_id,
        tenant_id,
        current_user,
        TaskRescheduleRequest(new_due_at=due_at, reason=req.reason),
    )
