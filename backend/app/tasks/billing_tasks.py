from datetime import timedelta, timezone, datetime
import logging
from app.worker import celery_app
from app.core.database import SessionLocal
from app.models.organization import Subscription
from app.services.billing_service import VALID_TRANSITIONS, transition_subscription

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.billing.subscription_monitor")
def subscription_monitor():
    """
    Scheduled job to monitor subscriptions.
    - Transitions expired trial/active subscriptions to EXPIRED.
    - Sends notifications for approaching expiries (30, 15, 7, 3, 1 day) -> placeholder for notification service
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        
        # 1. Expire outdated subscriptions
        expiring_subs = db.query(Subscription).filter(
            Subscription.status.in_(["TRIALING", "ACTIVE", "GRACE_PERIOD"]),
            Subscription.current_period_end < now
        ).all()

        expired_count = 0
        for sub in expiring_subs:
            try:
                transition_subscription(db, sub, "EXPIRED")
                expired_count += 1
            except Exception as e:
                logger.error(f"Failed to expire subscription {sub.id}: {str(e)}")
        
        # 2. Find subscriptions expiring soon (Notifications)
        # e.g., 3 days warning
        three_days_from_now = now + timedelta(days=3)
        three_days_plus_1h = three_days_from_now + timedelta(hours=1)
        
        warnings = db.query(Subscription).filter(
            Subscription.status.in_(["ACTIVE", "TRIALING"]),
            Subscription.current_period_end >= three_days_from_now,
            Subscription.current_period_end < three_days_plus_1h
        ).all()
        
        for sub in warnings:
            logger.info(f"[NOTIFICATION] Subscription {sub.id} (Org: {sub.organization_id}) expires in ~3 days")
            # In real system: send email or in-app notification

        logger.info(f"Subscription monitor completed. Expired {expired_count} subs.")
        return {"expired": expired_count, "warnings_issued": len(warnings)}
    finally:
        db.close()


@celery_app.task(name="tasks.billing.billing_reconciliation")
def billing_reconciliation_job():
    """
    Scheduled job to reconcile payment transactions against subscription status.
    If a transaction failed but subscription is ACTIVE, raises a MISMATCH alert.
    """
    db = SessionLocal()
    try:
        from app.models.billing import PaymentTransaction
        
        # Look for FAILED transactions linked to an ACTIVE subscription
        mismatches = db.query(PaymentTransaction).join(Subscription).filter(
            PaymentTransaction.status == "FAILED",
            Subscription.status == "ACTIVE"
        ).all()
        
        for tx in mismatches:
            logger.warning(
                f"[BILLING_MISMATCH] Organization {tx.organization_id} has an ACTIVE subscription {tx.subscription_id} "
                f"but a FAILED payment transaction {tx.id}."
            )
            # Future: generate admin_alerts "BILLING_MISMATCH" record for Super Admin action center
            
        return {"mismatches_found": len(mismatches)}
    finally:
        db.close()
