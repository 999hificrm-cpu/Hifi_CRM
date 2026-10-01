from typing import Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.organization import Subscription, Organization, Plan

# Legal transitions per the billing architecture rules
VALID_TRANSITIONS = {
    "TRIALING": ["ACTIVE", "EXPIRED", "SUSPENDED", "CANCELLED"],
    "ACTIVE": ["PAST_DUE", "SUSPENDED", "CANCELLED"],
    "PAST_DUE": ["ACTIVE", "GRACE_PERIOD", "SUSPENDED", "CANCELLED"],
    "GRACE_PERIOD": ["ACTIVE", "EXPIRED", "SUSPENDED", "CANCELLED"],
    "EXPIRED": ["ACTIVE"],
    "SUSPENDED": ["ACTIVE", "CANCELLED"],
    "CANCELLED": ["ACTIVE"] # re-activation
}

def utc_now():
    return datetime.now(timezone.utc)

def start_trial(db: Session, organization_id: str, plan_code: str = "TRIAL", days: int = 3) -> Subscription:
    """
    Start a 3-day trial for an organization.
    """
    plan = db.query(Plan).filter(Plan.code == plan_code.upper()).first()
    # Fallback to the first plan if specific TRIAL plan doesn't exist
    if not plan:
        plan = db.query(Plan).first()
        if not plan:
            raise ValueError("No plans configured in the system.")
            
    now = utc_now()
    trial_end = now + timedelta(days=days)
    
    sub = db.query(Subscription).filter(Subscription.organization_id == organization_id).first()
    if not sub:
        sub = Subscription(
            organization_id=organization_id,
            plan_id=plan.id,
            status="TRIALING",
            current_period_start=now,
            current_period_end=trial_end,
            seats_purchased=plan.seat_limit,
            pull_quota_monthly=plan.monthly_pull_quota
        )
        db.add(sub)
    else:
        # Update existing to trial (typically used if re-trialing or upgrading an empty state)
        sub.status = "TRIALING"
        sub.plan_id = plan.id
        sub.current_period_start = now
        sub.current_period_end = trial_end
        sub.seats_purchased = plan.seat_limit
        sub.pull_quota_monthly = plan.monthly_pull_quota
        
    db.commit()
    db.refresh(sub)
    return sub

def grant_full_access(db: Session, organization_id: str) -> Subscription:
    """
    Grant 10-year enterprise access for an organization.
    """
    plan = db.query(Plan).filter(Plan.code == "ENTERPRISE").first()
    if not plan:
        plan = db.query(Plan).first()
        if not plan:
            raise ValueError("No plans configured in the system.")
            
    now = utc_now()
    end_date = now + timedelta(days=365 * 10)
    
    sub = db.query(Subscription).filter(Subscription.organization_id == organization_id).first()
    if not sub:
        sub = Subscription(
            organization_id=organization_id,
            plan_id=plan.id,
            status="ACTIVE",
            current_period_start=now,
            current_period_end=end_date,
            seats_purchased=1000,
            pull_quota_monthly=1000000
        )
        db.add(sub)
    else:
        sub.status = "ACTIVE"
        sub.plan_id = plan.id
        sub.current_period_start = now
        sub.current_period_end = end_date
        sub.seats_purchased = 1000
        sub.pull_quota_monthly = 1000000
        
    db.commit()
    db.refresh(sub)
    return sub

def transition_subscription(db: Session, subscription: Subscription, new_status: str) -> Subscription:
    """
    Safely transition a subscription to a new status.
    """
    new_status = new_status.upper()
    current_status = subscription.status.upper()
    
    if new_status == current_status:
        return subscription
        
    if new_status not in VALID_TRANSITIONS.get(current_status, []):
        raise ValueError(f"Invalid subscription status transition from {current_status} to {new_status}")
        
    subscription.status = new_status
    db.commit()
    db.refresh(subscription)
    
    # Audit log should ideally be recorded here by the caller, or imported audit service
    # We will let the caller log the administrative action for now.
    
    return subscription
