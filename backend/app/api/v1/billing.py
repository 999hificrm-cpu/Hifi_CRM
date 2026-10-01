from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.deps import get_db, require_super_admin
from app.models.user import User
from app.models.billing import BillingEvent

router = APIRouter(prefix="/billing", tags=["Billing"])

@router.post("/webhooks/{provider}")
async def receive_billing_webhook(
    provider: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Generic webhook receiver for payment providers (e.g. stripe, razorpay).
    Records the event for asynchronous or synchronous processing.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    # In a real integration, we'd verify the provider's signature here (e.g., Stripe-Signature)
    
    event = BillingEvent(
        provider=provider.lower(),
        event_type=payload.get("type", "unknown_event"),
        payload=payload,
        processed_status="PENDING"
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # In the future: Dispatch to Celery to process the billing event asynchronously
    # process_billing_event.delay(event.id)

    return {"success": True, "event_id": event.id}


@router.get("/events")
def list_billing_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Super Admin route to view webhook events"""
    events = db.query(BillingEvent).order_by(BillingEvent.created_at.desc()).limit(100).all()
    return events
