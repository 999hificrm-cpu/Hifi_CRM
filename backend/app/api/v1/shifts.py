from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timezone

from app.core.deps import get_db, get_current_user, get_tenant_id
from app.models.user import User
from app.models.session import AttendanceSession, BreakSession
from app.core.business_time import organization_business_date, organization_day_bounds_utc

def to_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

router = APIRouter(prefix="/shift", tags=["Telecaller Shifts"])

@router.get("/status")
def get_shift_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), tenant_id: str = Depends(get_tenant_id)):
    now = datetime.now(timezone.utc)
    today = organization_business_date(db, tenant_id, now)
    
    active_shift = db.query(AttendanceSession).filter(
        AttendanceSession.organization_id == tenant_id,
        AttendanceSession.user_id == current_user.id,
        AttendanceSession.date == today,
        AttendanceSession.logout_at == None
    ).first()
    
    active_break = db.query(BreakSession).filter(
        BreakSession.organization_id == tenant_id,
        BreakSession.user_id == current_user.id,
        BreakSession.ended_at == None
    ).first()
    
    return {
        "is_active": active_shift is not None,
        "is_on_break": active_break is not None,
        "shift_started_at": active_shift.login_at if active_shift else None,
        "break_started_at": active_break.started_at if active_break else None
    }

@router.post("/start")
def start_shift(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), tenant_id: str = Depends(get_tenant_id)):
    now = datetime.now(timezone.utc)
    today = organization_business_date(db, tenant_id, now)
    
    # Check if already active shift today
    existing = db.query(AttendanceSession).filter(
        AttendanceSession.organization_id == tenant_id,
        AttendanceSession.user_id == current_user.id,
        AttendanceSession.date == today,
        AttendanceSession.logout_at == None
    ).first()
    
    if existing:
        return {"status": "already_started", "session_id": existing.id}
        
    new_session = AttendanceSession(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        date=today,
        login_at=now
    )
    db.add(new_session)
    try:
        db.commit()
    except IntegrityError:
        # The partial unique index is the final concurrency guard.  A second
        # request returns the already-open server session rather than creating
        # another one.
        db.rollback()
        existing = db.query(AttendanceSession).filter(
            AttendanceSession.organization_id == tenant_id,
            AttendanceSession.user_id == current_user.id,
            AttendanceSession.date == today,
            AttendanceSession.logout_at.is_(None),
        ).first()
        if existing:
            return {"status": "already_started", "session_id": existing.id}
        raise
    db.refresh(new_session)
    return {"status": "started", "session_id": new_session.id}

@router.post("/end")
def end_shift(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), tenant_id: str = Depends(get_tenant_id)):
    now = datetime.now(timezone.utc)
    today = organization_business_date(db, tenant_id, now)
    
    existing = db.query(AttendanceSession).filter(
        AttendanceSession.organization_id == tenant_id,
        AttendanceSession.user_id == current_user.id,
        AttendanceSession.date == today,
        AttendanceSession.logout_at == None
    ).first()
    
    if not existing:
        raise HTTPException(status_code=400, detail="No active shift found")
        
    existing.logout_at = now
    # A shift cannot retain an open break after it has ended.
    db.query(BreakSession).filter(
        BreakSession.organization_id == tenant_id,
        BreakSession.user_id == current_user.id,
        BreakSession.ended_at.is_(None),
    ).update({BreakSession.ended_at: now}, synchronize_session=False)
    db.commit()
    return {"status": "ended", "session_id": existing.id}

@router.post("/break-start")
def start_break(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), tenant_id: str = Depends(get_tenant_id)):
    now = datetime.now(timezone.utc)
    
    active_shift = db.query(AttendanceSession).filter(
        AttendanceSession.organization_id == tenant_id,
        AttendanceSession.user_id == current_user.id,
        AttendanceSession.logout_at.is_(None),
    ).first()
    if not active_shift:
        raise HTTPException(status_code=400, detail="Start a shift before starting a break")

    existing = db.query(BreakSession).filter(
        BreakSession.organization_id == tenant_id,
        BreakSession.user_id == current_user.id,
        BreakSession.ended_at == None
    ).first()
    
    if existing:
        return {"status": "already_on_break", "session_id": existing.id}
        
    new_break = BreakSession(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        started_at=now
    )
    db.add(new_break)
    db.commit()
    db.refresh(new_break)
    return {"status": "break_started", "session_id": new_break.id}

@router.post("/break-end")
def end_break(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), tenant_id: str = Depends(get_tenant_id)):
    now = datetime.now(timezone.utc)
    
    existing = db.query(BreakSession).filter(
        BreakSession.organization_id == tenant_id,
        BreakSession.user_id == current_user.id,
        BreakSession.ended_at == None
    ).first()
    
    if not existing:
        raise HTTPException(status_code=400, detail="No active break found")
        
    existing.ended_at = now
    db.commit()
    return {"status": "break_ended", "session_id": existing.id}


# Productivity Rollup (Problem 11)
from typing import Optional
from sqlalchemy import func
from app.core.deps import get_tenant_id
from app.models.activity import Activity
from app.models.call_record import CallRecord


@router.get("/productivity")
def get_productivity_report(
    user_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Problem 11: Explicit 4-bucket productivity session rollup:
    Total Shift Time, Talk Time, Break Time, and Idle/Wrap-up.
    Also returns activity breakdown and connection rate.
    """
    target_user_id = user_id if (user_id and current_user.tenant_role in ("ORG_ADMIN", "SALES_MANAGER", "SUPER_ADMIN")) else current_user.id
    now = datetime.now(timezone.utc)
    today = organization_business_date(db, tenant_id, now)
    try:
        range_start_date = date.fromisoformat(from_date) if from_date else today
        range_end_date = date.fromisoformat(to_date) if to_date else range_start_date
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="from_date and to_date must use YYYY-MM-DD") from exc
    if range_end_date < range_start_date:
        raise HTTPException(status_code=422, detail="to_date must be on or after from_date")

    range_start, _ = organization_day_bounds_utc(db, tenant_id, range_start_date)
    _, range_end = organization_day_bounds_utc(db, tenant_id, range_end_date)

    # 1. Total Shift Time
    attendance = db.query(AttendanceSession).filter(
        AttendanceSession.organization_id == tenant_id,
        AttendanceSession.user_id == target_user_id,
        AttendanceSession.date >= range_start_date,
        AttendanceSession.date <= range_end_date,
    ).all()
    total_shift_seconds = 0
    for s in attendance:
        login_at = to_utc(s.login_at)
        logout_at = to_utc(s.logout_at)
        s_date = s.date.date() if isinstance(s.date, datetime) else s.date
        end = logout_at or (now if s_date == today else range_end)
        if end and login_at:
            clipped_start = max(login_at, range_start)
            clipped_end = min(end, range_end)
            total_shift_seconds += max(0, int((clipped_end - clipped_start).total_seconds()))

    # 2. Break Time
    breaks = db.query(BreakSession).filter(
        BreakSession.organization_id == tenant_id,
        BreakSession.user_id == target_user_id,
        BreakSession.started_at >= range_start,
        BreakSession.started_at <= range_end,
    ).all()
    total_break_seconds = 0
    for b in breaks:
        started_at = to_utc(b.started_at)
        ended_at = to_utc(b.ended_at)
        end = ended_at or min(now, range_end)
        if end and started_at:
            total_break_seconds += max(0, int((min(end, range_end) - max(started_at, range_start)).total_seconds()))

    # 3. Talk Time (Verified telephony call_records)
    talk_time_seconds = db.query(func.sum(CallRecord.duration_seconds)).filter(
        CallRecord.organization_id == tenant_id,
        CallRecord.user_id == target_user_id,
        CallRecord.started_at >= range_start,
        CallRecord.started_at <= range_end,
    ).scalar() or 0

    # 4. Idle / Wrap-up
    idle_wrap_seconds = max(0, total_shift_seconds - (talk_time_seconds + total_break_seconds))

    # Activity Counts Grouped by Type
    act_counts = db.query(
        Activity.activity_type, func.count(Activity.id)
    ).filter(
        Activity.organization_id == tenant_id,
        Activity.user_id == target_user_id,
        Activity.occurred_at >= range_start,
        Activity.occurred_at <= range_end,
    ).group_by(Activity.activity_type).all()

    activity_breakdown = {act_type: count for act_type, count in act_counts}

    call_query = db.query(CallRecord).filter(
        CallRecord.organization_id == tenant_id,
        CallRecord.user_id == target_user_id,
        CallRecord.started_at >= range_start,
        CallRecord.started_at <= range_end,
        CallRecord.disposition != "INITIATED",
    )
    total_calls = call_query.count()
    connected_calls = call_query.filter(
        CallRecord.disposition.in_(["CONNECTED", "INTERESTED", "CALLBACK", "PROPOSAL_SENT"])
    ).count()

    connection_rate = round((connected_calls / total_calls * 100), 1) if total_calls > 0 else 0.0

    return {
        "user_id": target_user_id,
        "date": str(range_start_date) if range_start_date == range_end_date else None,
        "from_date": str(range_start_date),
        "to_date": str(range_end_date),
        "total_shift_minutes": total_shift_seconds // 60,
        "talk_time_minutes": talk_time_seconds // 60,
        "break_time_minutes": total_break_seconds // 60,
        "idle_wrap_minutes": idle_wrap_seconds // 60,
        "connection_rate_pct": connection_rate,
        "total_calls": total_calls,
        "connected_calls": connected_calls,
        "activity_breakdown": activity_breakdown,
        "chart_buckets": [
            {"label": "Talk Time", "minutes": talk_time_seconds // 60, "color": "#10b981"},
            {"label": "Break Time", "minutes": total_break_seconds // 60, "color": "#f59e0b"},
            {"label": "Idle / Wrap-up", "minutes": idle_wrap_seconds // 60, "color": "#6366f1"},
        ]
    }
