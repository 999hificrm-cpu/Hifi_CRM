from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException, status

from app.models.activity import Activity
from app.models.lead import Lead
from app.models.user import User
from app.models.audit import AuditLog, RadarEvent
from app.models.base import utc_now, generate_uuid
from app.schemas.activity import ActivityCreate, ActivityOut
from app.core.deps import ensure_lead_access


def create_activity(
    db: Session,
    organization_id: str,
    user: User,
    data: ActivityCreate
) -> ActivityOut:
    lead = None
    if data.lead_id:
        lead = db.query(Lead).filter(
            Lead.id == data.lead_id,
            Lead.organization_id == organization_id
        ).with_for_update().first()
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
        ensure_lead_access(db, lead, user, organization_id)

    now = utc_now()
    act_id = generate_uuid()
    company_id = lead.company_id if lead else data.company_id
    contact_id = lead.contact_id if lead else data.contact_id
    if not lead and company_id:
        from app.models.company import Company
        if not db.query(Company.id).filter(
            Company.id == company_id,
            Company.organization_id == organization_id,
        ).first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    if not lead and contact_id:
        from app.models.contact import Contact
        if not db.query(Contact.id).filter(
            Contact.id == contact_id,
            Contact.organization_id == organization_id,
        ).first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    act_type = data.activity_type.upper()
    direction = data.direction or "OUTBOUND"
    act_status = data.status or "COMPLETED"
    duration = data.duration_seconds or 0
    meta = data.metadata_json or {}

    activity = Activity(
        id=act_id,
        organization_id=organization_id,
        lead_id=data.lead_id,
        company_id=company_id,
        contact_id=contact_id,
        user_id=user.id,
        activity_type=act_type,
        subject=data.subject,
        description=data.description,
        direction=direction,
        status=act_status,
        duration_seconds=duration,
        metadata_json=meta,
        occurred_at=now,
        created_at=now
    )
    db.add(activity)

    # CallRecord is the authoritative KPI source.  A native dial creates an
    # INITIATED row; recording the outcome finalizes it.  Direct/manual outcome
    # clients still get a CallRecord, so targets and EOD never depend on an
    # Activity-only counter.
    if act_type == "CALL" and lead:
        from app.models.call_record import CallRecord

        from sqlalchemy import or_, and_
        from datetime import timedelta
        
        recent_threshold = now - timedelta(minutes=60)
        call_record = db.query(CallRecord).filter(
            CallRecord.organization_id == organization_id,
            CallRecord.lead_id == lead.id,
            CallRecord.user_id == user.id,
            or_(
                CallRecord.ended_at.is_(None),
                and_(
                    CallRecord.provider != "MANUAL_OUTCOME",
                    CallRecord.started_at >= recent_threshold
                )
            )
        ).order_by(CallRecord.started_at.desc()).with_for_update().first()
        if not call_record:
            call_record = CallRecord(
                organization_id=organization_id,
                lead_id=lead.id,
                contact_id=lead.contact_id,
                user_id=user.id,
                provider="MANUAL_OUTCOME",
                direction=direction,
                started_at=now,
            )
            db.add(call_record)
        call_record.disposition = act_status.upper()
        call_record.duration_seconds = duration
        if not call_record.ended_at:
            call_record.ended_at = now

        # Follow-up policies count authoritative CallRecord rows. Flush the
        # current outcome before evaluating a max-attempt policy so this call
        # participates in that count while remaining in the same transaction.
        db.flush()

    # Record Radar event if communication action (Call / WhatsApp / Email)
    if act_type in ("CALL", "WHATSAPP", "EMAIL"):
        radar_event = RadarEvent(
            organization_id=organization_id,
            actor_user_id=user.id,
            action=f"OUTBOUND_{act_type}",
            entity_type="LEAD",
            entity_id=lead.id if lead else organization_id,
            metadata_json={"activity_type": act_type, "duration": duration}
        )
        db.add(radar_event)

    # Outcome, stage, notes, call metrics and the explicit follow-up choice are
    # committed as one unit.  A failed stage/follow-up operation rolls the
    # whole outcome back instead of leaving partial history.
    if act_type == "CALL" and lead and data.pipeline_stage_id:
        from app.services.lead_service import change_lead_stage
        change_lead_stage(
            db,
            lead.id,
            data.pipeline_stage_id,
            organization_id,
            user,
            reason=f"Recorded with call outcome {act_status.upper()}",
            commit=False,
        )

    from app.services.followup_service import apply_followup_preset
    if act_type == "CALL":
        if data.followup_preset is not None:
            apply_followup_preset(db, activity, organization_id, user, data.followup_preset)

    db.commit()

    return ActivityOut(
        id=act_id,
        organization_id=organization_id,
        lead_id=data.lead_id,
        company_id=company_id,
        contact_id=contact_id,
        user_id=user.id,
        user_name=user.full_name,
        activity_type=act_type,
        subject=data.subject,
        description=data.description,
        direction=direction,
        status=act_status,
        duration_seconds=duration,
        metadata_json=meta,
        occurred_at=now,
        created_at=now
    )


def get_lead_timeline(db: Session, lead_id: str, organization_id: str) -> List[ActivityOut]:
    activities = db.query(Activity).filter(
        Activity.lead_id == lead_id,
        Activity.organization_id == organization_id
    ).order_by(desc(Activity.occurred_at)).all()

    result = []
    for act in activities:
        result.append(ActivityOut(
            id=act.id,
            organization_id=act.organization_id,
            lead_id=act.lead_id,
            company_id=act.company_id,
            contact_id=act.contact_id,
            user_id=act.user_id,
            user_name=act.user.full_name if act.user else None,
            activity_type=act.activity_type,
            subject=act.subject,
            description=act.description,
            direction=act.direction,
            status=act.status,
            duration_seconds=act.duration_seconds,
            metadata_json=act.metadata_json,
            occurred_at=act.occurred_at,
            created_at=act.created_at
        ))
    return result


def list_activities(
    db: Session,
    organization_id: str,
    user_id: Optional[str] = None,
    activity_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
) -> List[ActivityOut]:
    query = db.query(Activity).filter(Activity.organization_id == organization_id)
    if user_id:
        query = query.filter(Activity.user_id == user_id)
    if activity_type:
        query = query.filter(Activity.activity_type == activity_type.upper())

    items = query.order_by(desc(Activity.occurred_at)).offset(skip).limit(limit).all()
    return [
        ActivityOut(
            id=act.id,
            organization_id=act.organization_id,
            lead_id=act.lead_id,
            company_id=act.company_id,
            contact_id=act.contact_id,
            user_id=act.user_id,
            user_name=act.user.full_name if act.user else None,
            activity_type=act.activity_type,
            subject=act.subject,
            description=act.description,
            direction=act.direction,
            status=act.status,
            duration_seconds=act.duration_seconds,
            metadata_json=act.metadata_json,
            occurred_at=act.occurred_at,
            created_at=act.created_at
        )
        for act in items
    ]
