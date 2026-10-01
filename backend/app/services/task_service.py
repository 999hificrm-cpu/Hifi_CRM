from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.task import Task
from app.models.lead import Lead
from app.models.user import User
from app.models.activity import Activity
from app.models.audit import AuditLog
from app.schemas.task import TaskCreate, TaskUpdate, TaskRescheduleRequest, TaskOut


def _ensure_task_access(db: Session, task: Task, actor_user: User, organization_id: str) -> None:
    if actor_user.tenant_role != "TELECALLER":
        return
    from app.core.business_time import organization_business_date
    from app.core.deps import ensure_lead_access
    from app.models.delegation import AbsenceDelegation

    today = organization_business_date(db, organization_id)
    task_is_delegated = None
    if task.assigned_to != actor_user.id:
        task_is_delegated = db.query(AbsenceDelegation.id).filter(
            AbsenceDelegation.organization_id == organization_id,
            AbsenceDelegation.absent_user_id == task.assigned_to,
            AbsenceDelegation.cover_user_id == actor_user.id,
            AbsenceDelegation.start_date <= today,
            AbsenceDelegation.end_date >= today,
        ).first()
    if task.assigned_to != actor_user.id and not task_is_delegated:
        # Do not reveal whether a task outside the caller's worklist exists.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.lead_id:
        lead = db.query(Lead).filter(
            Lead.id == task.lead_id,
            Lead.organization_id == organization_id,
        ).first()
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        ensure_lead_access(db, lead, actor_user, organization_id)


def create_task(
    db: Session,
    organization_id: str,
    creator_user: User,
    data: TaskCreate
) -> Task:
    lead = None
    if data.lead_id:
        lead = db.query(Lead).filter(
            Lead.id == data.lead_id,
            Lead.organization_id == organization_id
        ).with_for_update().first()
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
        from app.core.deps import ensure_lead_access
        ensure_lead_access(db, lead, creator_user, organization_id)

    assigned_to = data.assigned_to or creator_user.id
    if creator_user.tenant_role == "TELECALLER":
        assigned_to = creator_user.id
    assignee = db.query(User).filter(
        User.id == assigned_to,
        User.organization_id == organization_id,
        User.deleted_at.is_(None),
    ).with_for_update().first()
    if not assignee:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee not found in organization")

    if not lead and (data.company_id or data.contact_id):
        from app.models.company import Company
        from app.models.contact import Contact
        if data.company_id and not db.query(Company.id).filter(
            Company.id == data.company_id, Company.organization_id == organization_id
        ).first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        if data.contact_id and not db.query(Contact.id).filter(
            Contact.id == data.contact_id, Contact.organization_id == organization_id
        ).first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    task = Task(
        organization_id=organization_id,
        lead_id=data.lead_id,
        company_id=data.company_id or (lead.company_id if lead else None),
        contact_id=data.contact_id or (lead.contact_id if lead else None),
        task_type=data.task_type or "FOLLOW_UP",
        title=data.title.strip(),
        description=data.description,
        priority=data.priority or "MEDIUM",
        status="PENDING",
        due_at=data.due_at,
        assigned_to=assigned_to,
        created_by=creator_user.id
    )

    # Idempotency: a lead has one authoritative active follow-up.  Update the
    # existing row in-place so repeated UI/policy requests cannot create a
    # second active task or erase the historical record.
    if task.task_type == "FOLLOW_UP" and task.lead_id:
        existing = db.query(Task).filter(
            Task.organization_id == organization_id,
            Task.lead_id == task.lead_id,
            Task.task_type == "FOLLOW_UP",
            Task.status == "PENDING"
        ).with_for_update().order_by(Task.created_at.desc()).first()
        if existing:
            existing.title = task.title
            existing.description = task.description
            existing.priority = task.priority
            existing.due_at = task.due_at
            existing.assigned_to = task.assigned_to
            db.commit()
            db.refresh(existing)
            return existing

    db.add(task)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if task.task_type == "FOLLOW_UP" and task.lead_id:
            existing = db.query(Task).filter(
                Task.organization_id == organization_id,
                Task.lead_id == task.lead_id,
                Task.task_type == "FOLLOW_UP",
                Task.status == "PENDING",
            ).first()
            if existing:
                return existing
        raise
    try:
        db.refresh(task)
    except Exception:
        pass
    return task


def complete_task(
    db: Session,
    task_id: str,
    organization_id: str,
    actor_user: User
) -> Task:
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.organization_id == organization_id
    ).with_for_update().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    _ensure_task_access(db, task, actor_user, organization_id)

    if task.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Follow-up is no longer active")

    task.status = "COMPLETED"
    task.completed_at = datetime.now(timezone.utc)
    if task.task_type == "FOLLOW_UP":
        db.add(Activity(
            organization_id=organization_id,
            lead_id=task.lead_id,
            company_id=task.company_id,
            contact_id=task.contact_id,
            user_id=actor_user.id,
            activity_type="TASK",
            subject="Follow-up completed",
            description=task.title,
            status="COMPLETED",
        ))
        db.add(AuditLog(
            organization_id=organization_id,
            user_id=actor_user.id,
            action="FOLLOWUP_COMPLETED",
            entity_type="TASK",
            entity_id=task.id,
            old_values={"status": "PENDING", "due_at": task.due_at.isoformat() if task.due_at else None},
            new_values={"status": "COMPLETED"},
        ))
    db.commit()
    try:
        db.refresh(task)
    except Exception:
        pass
    return task


def reschedule_task(
    db: Session,
    task_id: str,
    organization_id: str,
    actor_user: User,
    data: TaskRescheduleRequest
) -> Task:
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.organization_id == organization_id
    ).with_for_update().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    _ensure_task_access(db, task, actor_user, organization_id)

    if task.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Follow-up is no longer active")
    new_due = data.new_due_at
    if new_due.tzinfo is None:
        new_due = new_due.replace(tzinfo=timezone.utc)
    if new_due <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Follow-up due time must be in the future")

    old_due = task.due_at.isoformat() if task.due_at else None
    task.reschedule_count += 1
    new_history = list(task.reschedule_history or [])
    new_history.append({
        "old_due_at": old_due,
        "new_due_at": new_due.isoformat(),
        "reason": data.reason,
        "changed_by": actor_user.id,
        "changed_by_name": actor_user.full_name,
        "changed_at": datetime.now(timezone.utc).isoformat()
    })
    task.reschedule_history = new_history
    task.due_at = new_due
    task.status = "PENDING"
    if task.task_type == "FOLLOW_UP":
        db.add(Activity(
            organization_id=organization_id,
            lead_id=task.lead_id,
            company_id=task.company_id,
            contact_id=task.contact_id,
            user_id=actor_user.id,
            activity_type="TASK",
            subject="Follow-up rescheduled",
            description=f"Moved from {old_due or 'unscheduled'} to {new_due.isoformat()}. {data.reason or ''}".strip(),
            status="COMPLETED",
        ))
        db.add(AuditLog(
            organization_id=organization_id,
            user_id=actor_user.id,
            action="FOLLOWUP_RESCHEDULED",
            entity_type="TASK",
            entity_id=task.id,
            old_values={"due_at": old_due},
            new_values={"due_at": new_due.isoformat(), "reason": data.reason},
        ))
    db.commit()
    try:
        db.refresh(task)
    except Exception:
        pass
    return task


def list_tasks(
    db: Session,
    organization_id: str,
    assigned_to: Optional[str] = None,
    status_filter: Optional[str] = None,
    lead_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
) -> List[TaskOut]:
    query = db.query(Task).filter(Task.organization_id == organization_id)
    if assigned_to:
        query = query.filter(Task.assigned_to == assigned_to)
    if status_filter:
        query = query.filter(Task.status == status_filter.upper())
    if lead_id:
        query = query.filter(Task.lead_id == lead_id)

    tasks = query.order_by(Task.due_at.asc().nullslast()).offset(skip).limit(limit).all()
    return [
        TaskOut(
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
        for t in tasks
    ]
