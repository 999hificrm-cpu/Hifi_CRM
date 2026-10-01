from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone

from app.core.deps import get_db, get_current_user, get_tenant_id, ensure_lead_access
from app.core.config import settings
from app.core.webhooks import verify_hmac_webhook
from app.models.user import User
from app.models.lead import Lead
from app.models.call_record import CallRecord
from app.models.activity import Activity
from app.core.business_time import organization_business_date, organization_day_bounds_utc

router = APIRouter(prefix="/telephony", tags=["Telephony"])


class DialRequest(BaseModel):
    lead_id: str
    contact_phone_id: Optional[str] = None


@router.post("/dial")
def initiate_call(
    data: DialRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    lead = db.query(Lead).filter(
        Lead.id == data.lead_id,
        Lead.organization_id == tenant_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    ensure_lead_access(db, lead, current_user, tenant_id)
        
    # Problem 3 & 5: Log the call attempt immediately as Activity and CallRecord
    call_record = CallRecord(
        organization_id=tenant_id,
        lead_id=lead.id,
        contact_id=lead.contact_id,
        user_id=current_user.id,
        provider="NATIVE_DIALER",
        direction="OUTBOUND",
        started_at=datetime.now(timezone.utc),
        disposition="INITIATED"
    )
    db.add(call_record)

    # Immediate Activity row with status='SCHEDULED'
    activity = Activity(
        organization_id=tenant_id,
        lead_id=lead.id,
        contact_id=lead.contact_id,
        user_id=current_user.id,
        activity_type="CALL",
        subject=f"Outbound Call Initiated to {lead.contact_name or lead.title}",
        description="Call dialed via native application bridge.",
        status="SCHEDULED",
        metadata_json={"call_record_id": call_record.id}
    )
    db.add(activity)
    db.commit()
    db.refresh(call_record)
    
    phone = lead.contact_phone or ""
    clean_digits = "".join([c for c in phone if c.isdigit() or c == "+"])
    
    return {
        "status": "success",
        "call_record_id": call_record.id,
        "tel_url": f"tel:{clean_digits}" if clean_digits else None
    }


class WebhookPayload(BaseModel):
    call_id: Optional[str] = None
    call_record_id: Optional[str] = None
    status: Optional[str] = None
    disposition: Optional[str] = None
    duration: Optional[int] = None
    duration_seconds: Optional[int] = None
    recording_url: Optional[str] = None


@router.post("/webhook")
async def telephony_webhook(
    data: WebhookPayload,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Problem 5: Webhook receives real duration/status.
    Auto-updates CallRecord and logs CRM Activity timeline event.
    """
    await verify_hmac_webhook(request, settings.TELEPHONY_WEBHOOK_SECRET, "X-Telephony-Signature")
    target_id = data.call_id or data.call_record_id
    if not target_id:
        raise HTTPException(status_code=400, detail="Missing call_id or call_record_id")

    call_record = db.query(CallRecord).filter(
        or_(CallRecord.id == target_id, CallRecord.provider_call_id == target_id)
    ).first()

    disp = (data.status or data.disposition or "CONNECTED").upper()
    dur = data.duration if data.duration is not None else (data.duration_seconds or 0)

    if call_record:
        if data.call_id and not call_record.provider_call_id:
            call_record.provider_call_id = data.call_id

        call_record.disposition = disp
        call_record.duration_seconds = dur
        if not call_record.ended_at:
            call_record.ended_at = datetime.now(timezone.utc)
        if data.recording_url:
            call_record.recording_url = data.recording_url
        
        # Finalize the initiation activity instead of appending another raw
        # call row.  Provider retries therefore remain idempotent.
        activities = db.query(Activity).filter(
            Activity.organization_id == call_record.organization_id,
            Activity.lead_id == call_record.lead_id,
            Activity.user_id == call_record.user_id,
            Activity.activity_type == "CALL",
        ).order_by(Activity.occurred_at.desc()).limit(10).all()

        activity = next((a for a in activities if isinstance(a.metadata_json, dict) and a.metadata_json.get("call_record_id") == call_record.id), None)
        
        if not activity:
            activity = Activity(
                organization_id=call_record.organization_id,
                lead_id=call_record.lead_id,
                contact_id=call_record.contact_id,
                user_id=call_record.user_id,
                activity_type="CALL",
                metadata_json={"call_record_id": call_record.id}
            )
            db.add(activity)
        activity.subject = f"Outbound Call - {disp}"
        activity.description = f"Call completed. Telemetry duration: {dur} seconds."
        activity.duration_seconds = dur
        activity.status = "COMPLETED"
        db.commit()
        return {"status": "success", "call_record_id": call_record.id}

    return {"status": "ignored", "message": "Call record not found"}
    
    return {"status": "success"}


class TelecallerKPIsOut(BaseModel):
    calls_made_today: int
    talk_time_minutes: int
    high_interest_leads: int


@router.get("/my-kpis", response_model=TelecallerKPIsOut)
def get_my_kpis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    from sqlalchemy import func

    today = organization_business_date(db, tenant_id)
    day_start, day_end = organization_day_bounds_utc(db, tenant_id, today)
    calls_made = db.query(CallRecord).filter(
        CallRecord.organization_id == tenant_id,
        CallRecord.user_id == current_user.id,
        CallRecord.started_at >= day_start,
        CallRecord.started_at <= day_end,
        CallRecord.disposition != "INITIATED",
    ).count()

    talk_time_seconds = db.query(func.sum(CallRecord.duration_seconds)).filter(
        CallRecord.organization_id == tenant_id,
        CallRecord.user_id == current_user.id,
        CallRecord.started_at >= day_start,
        CallRecord.started_at <= day_end,
    ).scalar() or 0

    high_interest = db.query(CallRecord).filter(
        CallRecord.organization_id == tenant_id,
        CallRecord.user_id == current_user.id,
        CallRecord.disposition.in_(["INTERESTED", "CALLBACK", "PROPOSAL_SENT"]),
        CallRecord.started_at >= day_start,
        CallRecord.started_at <= day_end,
    ).count()

    return TelecallerKPIsOut(
        calls_made_today=calls_made,
        talk_time_minutes=talk_time_seconds // 60,
        high_interest_leads=high_interest
    )
