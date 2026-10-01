from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user, get_tenant_id
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskRescheduleRequest, TaskOut
from app.services.task_service import create_task, complete_task, reschedule_task, list_tasks

router = APIRouter(prefix="/tasks", tags=["Tasks & Follow-ups"])


@router.get("/", response_model=List[TaskOut])
def get_tasks(
    assigned_to: Optional[str] = None,
    status_filter: Optional[str] = None,
    lead_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    # Telecallers only see their own tasks by default
    if current_user.tenant_role == "TELECALLER":
        assigned_to = current_user.id
    return list_tasks(db, tenant_id, assigned_to, status_filter, lead_id, skip, limit)


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_new_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    t = create_task(db, tenant_id, current_user, data)
    return TaskOut(
        id=t.id,
        organization_id=t.organization_id,
        lead_id=t.lead_id,
        company_id=t.company_id,
        contact_id=t.contact_id,
        task_type=t.task_type,
        title=t.title,
        description=t.description,
        priority=t.priority,
        status=t.status,
        due_at=t.due_at,
        completed_at=t.completed_at,
        assigned_to=t.assigned_to,
        assigned_to_name=t.assignee.full_name if t.assignee else None,
        created_by=t.created_by,
        reschedule_count=t.reschedule_count,
        reschedule_history=t.reschedule_history or [],
        created_at=t.created_at,
        updated_at=t.updated_at
    )


@router.post("/{id}/complete", response_model=TaskOut)
def mark_task_complete(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    t = complete_task(db, id, tenant_id, current_user)
    return TaskOut(
        id=t.id,
        organization_id=t.organization_id,
        lead_id=t.lead_id,
        company_id=t.company_id,
        contact_id=t.contact_id,
        task_type=t.task_type,
        title=t.title,
        description=t.description,
        priority=t.priority,
        status=t.status,
        due_at=t.due_at,
        completed_at=t.completed_at,
        assigned_to=t.assigned_to,
        assigned_to_name=t.assignee.full_name if t.assignee else None,
        created_by=t.created_by,
        reschedule_count=t.reschedule_count,
        reschedule_history=t.reschedule_history or [],
        created_at=t.created_at,
        updated_at=t.updated_at
    )


@router.post("/{id}/reschedule", response_model=TaskOut)
def reschedule_existing_task(
    id: str,
    data: TaskRescheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    t = reschedule_task(db, id, tenant_id, current_user, data)
    return TaskOut(
        id=t.id,
        organization_id=t.organization_id,
        lead_id=t.lead_id,
        company_id=t.company_id,
        contact_id=t.contact_id,
        task_type=t.task_type,
        title=t.title,
        description=t.description,
        priority=t.priority,
        status=t.status,
        due_at=t.due_at,
        completed_at=t.completed_at,
        assigned_to=t.assigned_to,
        assigned_to_name=t.assignee.full_name if t.assignee else None,
        created_by=t.created_by,
        reschedule_count=t.reschedule_count,
        reschedule_history=t.reschedule_history or [],
        created_at=t.created_at,
        updated_at=t.updated_at
    )
