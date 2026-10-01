import os
import uuid
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timezone, timedelta
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, or_, and_, text

from app.core.deps import get_db, get_current_user, get_tenant_id, get_optional_tenant_id
from app.models.user import User
from app.models.lead import Lead
from app.models.lead_history import LeadStageHistory
from app.models.activity import Activity
from app.models.call_record import CallRecord
from app.models.task import Task, DailyCallPlan, DailyTask
from app.models.company import Company
from app.models.telecaller_target import TelecallerTarget
from app.models.availability import AvailabilityStatus, LeaveRequest
from app.models.delegation import AbsenceDelegation
from app.models.eod_report import EODReport
from app.models.ai import AIInsight
from app.models.base import generate_uuid, utc_now
from app.services.lead_service import serialize_lead
from app.services.activity_service import get_lead_timeline
from app.services.followup_service import active_followup_query, accessible_work_owner_ids
from app.core.business_time import organization_business_date, organization_day_bounds_utc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telecaller", tags=["Telecaller Engine & Operations"])


def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ==========================================
# 1. Targets & Daily Performance (Problem 2)
# ==========================================

class TelecallerTargetCreate(BaseModel):
    user_id: Optional[str] = None
    target_date: Optional[date] = None
    target_calls: Optional[int] = None
    target_connects: Optional[int] = None
    target_talk_time_minutes: Optional[int] = None
    target_qualified_leads: Optional[int] = None
    target_conversions: Optional[int] = None
    target_revenue: Optional[float] = 0.0


class TelecallerTargetUpdate(BaseModel):
    target_calls: Optional[int] = None
    target_connects: Optional[int] = None
    target_talk_time_minutes: Optional[int] = None
    target_qualified_leads: Optional[int] = None
    target_conversions: Optional[int] = None
    target_revenue: Optional[float] = None


class TelecallerTargetTodayOut(BaseModel):
    id: Optional[str] = None
    user_id: str
    target_date: str
    target_calls: int
    actual_calls: int
    target_connects: int
    actual_connects: int
    target_talk_time_minutes: int
    actual_talk_time_minutes: int
    target_conversions: int
    actual_conversions: int
    calls_progress_pct: float
    connects_progress_pct: float
    talk_time_progress_pct: float
    conversions_progress_pct: float
    is_configured: bool = True


@router.get("/targets/today", response_model=TelecallerTargetTodayOut)
def get_today_target(
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Computes today's target vs. actuals for the telecaller.
    Queries verified activity and lead progression records.
    """
    target_user_id = user_id if (user_id and current_user.tenant_role in ("ORG_ADMIN", "SALES_MANAGER", "SUPER_ADMIN")) else current_user.id
    today = organization_business_date(db, tenant_id)
    today_start, today_end = organization_day_bounds_utc(db, tenant_id, today)

    target_user = db.query(User).filter(
        User.id == target_user_id,
        User.organization_id == tenant_id,
    ).with_for_update().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target = db.query(TelecallerTarget).filter(
        TelecallerTarget.organization_id == tenant_id,
        TelecallerTarget.user_id == target_user_id,
        TelecallerTarget.target_date == today,
    ).first()
    # Legacy JSON values are migrated on read only when no authoritative row
    # exists.  All subsequent reads use the table.
    if not target and target_user.telecaller_targets:
        legacy = target_user.telecaller_targets
        target = TelecallerTarget(
            id=generate_uuid(), organization_id=tenant_id, user_id=target_user_id,
            target_date=today, target_calls=int(legacy.get("calls", 0) or 0),
            target_connects=int(legacy.get("connects", 0) or 0),
            target_talk_time_minutes=int(legacy.get("talk_time", 0) or 0),
            target_qualified_leads=int(legacy.get("qualified_leads", 0) or 0),
            target_conversions=int(legacy.get("conversions", 0) or 0),
            target_revenue=float(legacy.get("revenue", 0) or 0),
        )
        db.add(target)
        db.commit()
        db.refresh(target)
    is_configured = target is not None
    target_calls = (target.target_calls or 0) if target else 0
    target_connects = (target.target_connects or 0) if target else 0
    target_talk_time = (target.target_talk_time_minutes or 0) if target else 0
    target_conversions = (target.target_conversions or 0) if target else 0

    # Query real actuals from activities
    actual_calls = db.query(CallRecord).filter(
        CallRecord.organization_id == tenant_id,
        CallRecord.user_id == target_user_id,
        CallRecord.started_at >= today_start,
        CallRecord.started_at <= today_end,
        CallRecord.disposition != "INITIATED",
    ).count()

    actual_connects = db.query(CallRecord).filter(
        CallRecord.organization_id == tenant_id,
        CallRecord.user_id == target_user_id,
        CallRecord.started_at >= today_start,
        CallRecord.started_at <= today_end,
        CallRecord.disposition.in_(["CONNECTED", "INTERESTED", "CALLBACK", "PROPOSAL_SENT"]),
    ).count()

    talk_seconds = db.query(func.sum(CallRecord.duration_seconds)).filter(
        CallRecord.organization_id == tenant_id,
        CallRecord.user_id == target_user_id,
        CallRecord.started_at >= today_start,
        CallRecord.started_at <= today_end,
    ).scalar() or 0
    actual_talk_minutes = talk_seconds // 60

    # Conversions: leads owned or closed by user transitioned to WON today
    actual_conversions = db.query(Lead).filter(
        Lead.organization_id == tenant_id,
        Lead.owner_id == target_user_id,
        Lead.status == "WON",
        Lead.updated_at >= today_start,
        Lead.updated_at <= today_end
    ).count()

    calls_pct = round(min(100.0, (actual_calls / target_calls * 100)) if target_calls > 0 else 0, 1)
    conn_pct = round(min(100.0, (actual_connects / target_connects * 100)) if target_connects > 0 else 0, 1)
    tt_pct = round(min(100.0, (actual_talk_minutes / target_talk_time * 100)) if target_talk_time > 0 else 0, 1)
    conv_pct = round(min(100.0, (actual_conversions / target_conversions * 100)) if target_conversions > 0 else 0, 1)

    return TelecallerTargetTodayOut(
        id=target.id if target else None,
        user_id=target_user_id,
        target_date=str(today),
        target_calls=target_calls,
        actual_calls=actual_calls,
        target_connects=target_connects,
        actual_connects=actual_connects,
        target_talk_time_minutes=target_talk_time,
        actual_talk_time_minutes=actual_talk_minutes,
        target_conversions=target_conversions,
        actual_conversions=actual_conversions,
        calls_progress_pct=calls_pct,
        connects_progress_pct=conn_pct,
        talk_time_progress_pct=tt_pct,
        conversions_progress_pct=conv_pct,
        is_configured=is_configured
    )




@router.get("/performance/today")
def get_today_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    return get_today_target(current_user.id, db, current_user, tenant_id)


# ==========================================
# 2. My Queue & Delegation Resolution (Problems 1, 8, 9)
# ==========================================

@router.get("/my-queue")
def get_my_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Returns only leads assigned to the telecaller, plus active delegated leads if covering an absent person.
    Strictly tenant-scoped and telecaller-isolated.
    """
    now = datetime.now(timezone.utc)
    today_date = organization_business_date(db, tenant_id, now)

    # Find users who delegated their work to current user
    delegators = db.query(AbsenceDelegation.absent_user_id).filter(
        AbsenceDelegation.organization_id == tenant_id,
        AbsenceDelegation.cover_user_id == current_user.id,
        AbsenceDelegation.start_date <= today_date,
        AbsenceDelegation.end_date >= today_date
    ).all()
    delegator_ids = [d[0] for d in delegators]

    query = db.query(Lead).filter(
        Lead.organization_id == tenant_id,
        or_(
            Lead.owner_id == current_user.id,
            Lead.owner_id.in_(delegator_ids) if delegator_ids else False
        ),
        Lead.status != "ARCHIVED"
    ).order_by(
        desc(Lead.priority == "URGENT"),
        desc(Lead.priority == "HIGH"),
        desc(Lead.score),
        Lead.updated_at
    )

    leads = query.limit(200).all()
    return [serialize_lead(l, current_user, db) for l in leads]


# ==========================================
# 3. Daily Execution Queue (Problem 18)
# ==========================================

class DailyQueueItem(BaseModel):
    lead_id: str
    task_id: Optional[str] = None
    source: str  # FOLLOWUP, NEW_LEAD, RETRY
    priority: str
    due_at: Optional[datetime] = None
    title: str
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    is_phone_masked: bool = True
    score: int = 0
    segment: Optional[str] = None
    lead_type: Optional[str] = None


class DailyQueueOut(BaseModel):
    total: int
    fresh_count: int
    followup_count: int
    items: List[DailyQueueItem]


@router.get("/queue/today", response_model=DailyQueueOut)
def get_daily_queue_today(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Builds the prioritized execution queue as a prioritized union of:
    1. All accessible active persisted follow-up tasks (PENDING)
    2. New leads assigned to telecaller
    3. Cadence retries / pending re-attempts
    """
    queue_owner_ids = accessible_work_owner_ids(db, tenant_id, current_user)

    items: List[DailyQueueItem] = []

    # 1. The worklist consumes the exact same active persisted population as
    # My Follow-ups.  Future callbacks remain visible and sort by due time.
    tasks = active_followup_query(db, tenant_id, current_user).order_by(
        desc(Task.priority == "HIGH"), Task.due_at.asc()
    ).all()

    processed_task_lead_ids = set()
    for t in tasks:
        if t.lead and t.lead_id not in processed_task_lead_ids:
            processed_task_lead_ids.add(t.lead_id)
            s_lead = serialize_lead(t.lead, current_user, db)
            items.append(DailyQueueItem(
                lead_id=t.lead.id,
                task_id=t.id,
                source="FOLLOWUP",
                priority=t.priority or "NORMAL",
                due_at=t.due_at,
                title=t.lead.title,
                company_name=t.lead.company_name,
                contact_name=t.lead.contact_name,
                contact_phone=s_lead.contact_phone,
                is_phone_masked=s_lead.is_phone_masked,
                score=t.lead.score or 0,
                segment=t.lead.segment,
                lead_type=t.lead.lead_type
            ))

    # 2. Fresh Leads Assigned to Caller (NEW or OPEN with no finalized CallRecord)
    from app.models.call_record import CallRecord
    subq = db.query(CallRecord.lead_id).filter(
        CallRecord.organization_id == tenant_id,
        CallRecord.disposition.notin_(["INITIATED", "PENDING"])
    ).subquery()

    new_leads = db.query(Lead).outerjoin(
        subq, Lead.id == subq.c.lead_id
    ).filter(
        Lead.organization_id == tenant_id,
        Lead.owner_id.in_(queue_owner_ids),
        Lead.deleted_at.is_(None),
        Lead.status.in_(["NEW", "OPEN"]),
        subq.c.lead_id == None
    ).order_by(desc(Lead.score), Lead.created_at.desc()).limit(50).all()

    existing_ids = {i.lead_id for i in items}
    for nl in new_leads:
        if nl.id not in existing_ids:
            s_lead = serialize_lead(nl, current_user, db)
            items.append(DailyQueueItem(
                lead_id=nl.id,
                source="NEW_LEAD",
                priority=nl.priority or "NORMAL",
                due_at=nl.created_at,
                title=nl.title,
                company_name=nl.company_name,
                contact_name=nl.contact_name,
                contact_phone=s_lead.contact_phone,
                is_phone_masked=s_lead.is_phone_masked,
                score=nl.score or 0,
                segment=nl.segment,
                lead_type=nl.lead_type
            ))

    # Sort final queue by priority: HIGH=1, NORMAL/MEDIUM=2, other=3
    def sort_key(item: DailyQueueItem):
        p_order = 1 if item.priority in ("HIGH", "URGENT") else (2 if item.priority in ("NORMAL", "MEDIUM") else 3)
        due = to_utc(item.due_at) or datetime.max.replace(tzinfo=timezone.utc)
        return (p_order, due)

    items.sort(key=sort_key)
    fresh_count = sum(item.source == "NEW_LEAD" for item in items)
    followup_count = sum(item.source == "FOLLOWUP" for item in items)
    return DailyQueueOut(
        total=len(items),
        fresh_count=fresh_count,
        followup_count=followup_count,
        items=items,
    )


@router.get("/queue/next")
def get_next_queue_lead(
    current_lead_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Eagerly loads the next dialable lead in sequence with eager-loaded pre-call context (last 5 activities,
    pending tasks, company, stage history).
    """
    queue = get_daily_queue_today(db, current_user, tenant_id).items
    if not queue:
        return {"lead": None, "has_next": False}

    next_item = queue[0]
    if current_lead_id:
        for idx, item in enumerate(queue):
            if item.lead_id == current_lead_id and idx + 1 < len(queue):
                next_item = queue[idx + 1]
                break

    # Eager load full context
    lead = db.query(Lead).options(
        joinedload(Lead.company),
        joinedload(Lead.tasks)
    ).filter(
        Lead.id == next_item.lead_id,
        Lead.organization_id == tenant_id
    ).first()

    if not lead:
        return {"lead": None, "has_next": False}

    timeline = get_lead_timeline(db, lead.id, tenant_id)
    stage_history = db.query(LeadStageHistory).filter(
        LeadStageHistory.lead_id == lead.id
    ).order_by(desc(LeadStageHistory.created_at)).all()

    # AI recommendation
    ai_action = db.query(AIInsight).filter(
        AIInsight.entity_type == "LEAD",
        AIInsight.entity_id == lead.id,
        AIInsight.insight_type == "NEXT_ACTION"
    ).order_by(desc(AIInsight.created_at)).first()

    return {
        "has_next": True,
        "lead": serialize_lead(lead, current_user, db),
        "source": next_item.source,
        "timeline": timeline[:5],
        "pending_tasks": [t.title for t in lead.tasks if t.status == "PENDING"],
        "stage_history_count": len(stage_history),
        "ai_recommendation": ai_action.output_data if ai_action and hasattr(ai_action, "output_data") else None
    }


# ==========================================
# 4. Next-Best-Action Engine (Problems 16 & 17)
# ==========================================

class NextActionItem(BaseModel):
    lead_id: str
    scheduled_time: str  # "NOW", "10:30", "12:00"
    company_name: str
    contact_name: str
    action_type: str  # "Call", "WhatsApp", "Email"
    action_reason: str
    score: float
    deal_value: float


@router.get("/next-actions", response_model=List[NextActionItem])
def get_next_best_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Ranks pending telecaller actions by multi-factor scoring:
    promised callback > lead stage/score > deal value > urgency/overdue duration.
    """
    now = datetime.now(timezone.utc)
    today = now.date()

    # Find tasks
    tasks = db.query(Task).join(Lead, Task.lead_id == Lead.id).filter(
        Task.organization_id == tenant_id,
        Task.assigned_to == current_user.id,
        Task.status.in_(["PENDING", "OVERDUE"])
    ).order_by(desc(Task.priority == "HIGH"), Task.due_at.asc()).limit(50).all()

    scored_actions: List[NextActionItem] = []
    processed_lead_ids = set()

    for t in tasks:
        lead = t.lead
        if not lead or lead.id in processed_lead_ids:
            continue

        processed_lead_ids.add(lead.id)

        base_score = float(lead.score or 50)
        value = float(lead.value or 0)
        value_weight = min(100.0, value / 1000.0)

        # Promised callback check
        is_callback = "callback" in (t.title or "").lower() or lead.status == "CALLBACK"
        callback_weight = 500.0 if is_callback else 0.0

        # Overdue weight
        urgency_weight = 0.0
        due_at = to_utc(t.due_at)
        if due_at:
            if due_at < now:
                diff_hours = (now - due_at).total_seconds() / 3600.0
                urgency_weight = min(300.0, diff_hours * 25.0)

        total_score = callback_weight + (base_score * 2.0) + value_weight + urgency_weight

        # Scheduled display time
        if not due_at or due_at <= now:
            time_display = "NOW"
        else:
            time_display = due_at.strftime("%H:%M")

        # Determine best channel
        action_type = "Call"
        if "whatsapp" in (t.title or "").lower() or "wa" in (t.title or "").lower():
            action_type = "WhatsApp"
        elif "email" in (t.title or "").lower():
            action_type = "Email"

        scored_actions.append(NextActionItem(
            lead_id=lead.id,
            scheduled_time=time_display,
            company_name=lead.company_name or "Individual",
            contact_name=lead.contact_name or lead.title,
            action_type=action_type,
            action_reason=t.title or "Scheduled follow-up",
            score=round(total_score, 1),
            deal_value=value
        ))

    scored_actions.sort(key=lambda x: (0 if x.scheduled_time == "NOW" else 1, -x.score))
    return scored_actions


# ==========================================
# 5. Availability & Leave Management (Problem 8)
# ==========================================

class AvailabilityUpdate(BaseModel):
    status: str  # AVAILABLE, ON_BREAK, OFFLINE, ABSENT, LEAVE, SUSPENDED


class LeaveRequestCreate(BaseModel):
    starts_at: datetime
    ends_at: datetime
    reason: Optional[str] = None


@router.get("/availability")
def get_my_availability(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    avail = db.query(AvailabilityStatus).filter(
        AvailabilityStatus.user_id == current_user.id
    ).first()
    return {
        "user_id": current_user.id,
        "status": avail.status if avail else "AVAILABLE",
        "updated_at": avail.updated_at if avail else None
    }


@router.put("/availability")
def update_my_availability(
    data: AvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    valid_statuses = ("AVAILABLE", "ON_BREAK", "OFFLINE", "ABSENT", "LEAVE", "SUSPENDED")
    st = data.status.upper()
    if st not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose from {valid_statuses}")

    avail = db.query(AvailabilityStatus).filter(
        AvailabilityStatus.user_id == current_user.id
    ).first()

    now = datetime.now(timezone.utc)
    if avail:
        avail.status = st
        avail.updated_at = now
    else:
        avail = AvailabilityStatus(
            user_id=current_user.id,
            organization_id=tenant_id,
            status=st,
            updated_at=now
        )
        db.add(avail)

    db.commit()
    return {"status": "success", "availability": st}


@router.post("/leave-requests")
def submit_leave_request(
    data: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    req = LeaveRequest(
        id=generate_uuid(),
        organization_id=tenant_id,
        user_id=current_user.id,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        reason=data.reason
    )
    db.add(req)
    db.commit()
    return {"status": "submitted", "request_id": req.id}


# ==========================================
# 6. Absence Delegations (Problem 9)
# ==========================================

class DelegationCreate(BaseModel):
    absent_user_id: str
    cover_user_id: str
    start_date: date
    end_date: date
    reason: Optional[str] = None


@router.post("/delegations")
def create_delegation(
    data: DelegationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    if not (current_user.is_org_admin or current_user.tenant_role in ("ORG_ADMIN", "SALES_MANAGER", "SUPER_ADMIN")):
        raise HTTPException(status_code=403, detail="Manager or Admin role required to create coverage delegations")

    if data.start_date > data.end_date:
        raise HTTPException(status_code=422, detail="Delegation start_date must not be after end_date")
    if data.absent_user_id == data.cover_user_id:
        raise HTTPException(status_code=422, detail="Absent and cover users must be different")
    users = db.query(User).filter(
        User.organization_id == tenant_id,
        User.id.in_([data.absent_user_id, data.cover_user_id]),
        User.tenant_role == "TELECALLER",
        User.status == "ACTIVE",
        User.deleted_at.is_(None),
    ).all()
    if len(users) != 2:
        raise HTTPException(status_code=400, detail="Both delegation users must be active telecallers in this organization")

    delegation = AbsenceDelegation(
        id=generate_uuid(),
        organization_id=tenant_id,
        absent_user_id=data.absent_user_id,
        cover_user_id=data.cover_user_id,
        start_date=data.start_date,
        end_date=data.end_date,
        reason=data.reason
    )
    db.add(delegation)
    db.commit()
    return {"status": "created", "delegation_id": delegation.id}


@router.get("/delegations/active")
def list_active_delegations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    today = organization_business_date(db, tenant_id)
    delegations = db.query(AbsenceDelegation).filter(
        AbsenceDelegation.organization_id == tenant_id,
        AbsenceDelegation.start_date <= today,
        AbsenceDelegation.end_date >= today
    )
    if current_user.tenant_role == "TELECALLER":
        delegations = delegations.filter(
            or_(
                AbsenceDelegation.absent_user_id == current_user.id,
                AbsenceDelegation.cover_user_id == current_user.id,
            )
        )
    delegations = delegations.all()

    return [
        {
            "id": d.id,
            "absent_user_id": d.absent_user_id,
            "absent_user_name": d.absent_user.full_name if d.absent_user else None,
            "cover_user_id": d.cover_user_id,
            "cover_user_name": d.cover_user.full_name if d.cover_user else None,
            "start_date": str(d.start_date),
            "end_date": str(d.end_date),
            "reason": d.reason
        }
        for d in delegations
    ]


# ==========================================
# 7. End of Day Reports (Problem 10)
# ==========================================

@router.get("/eod-report/today")
def get_my_today_eod_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    today = organization_business_date(db, tenant_id)
    report = db.query(EODReport).filter(
        EODReport.organization_id == tenant_id,
        EODReport.user_id == current_user.id,
        EODReport.report_date == today
    ).first()

    if not report:
        # Fallback to computing live snapshot
        target_info = get_today_target(current_user.id, db, current_user, tenant_id)
        return {
            "date": str(today),
            "user_id": current_user.id,
            "status": "in_progress",
            "calls_made": target_info.actual_calls,
            "connects": target_info.actual_connects,
            "talk_time_seconds": target_info.actual_talk_time_minutes * 60,
            "conversions": target_info.actual_conversions,
            "target_achievement_pct": target_info.calls_progress_pct,
            "ai_summary": "Active session in progress. Formal EOD report generates at end-of-day."
        }

    return {
        "id": report.id,
        "date": str(report.report_date),
        "user_id": report.user_id,
        "status": "final",
        "metrics": report.metrics_snapshot,
        "ai_summary": report.ai_summary,
        "created_at": report.created_at
    }
