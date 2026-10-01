import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.notifications import Notification, NotificationRule, NotificationDelivery
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def dispatch_notification(
    db: Session,
    organization_id: str,
    recipient_id: str,
    event_type: str,
    title: str,
    body: str = None,
    action_url: str = None,
    event_key: str = None
) -> Optional[Notification]:
    """
    Centralized dispatcher. Deduplicates based on event_key and recipient_id.
    """
    if event_key:
        # Check for deduplication
        existing = db.query(Notification).filter(
            Notification.recipient_id == recipient_id,
            Notification.event_key == event_key
        ).first()
        
        if existing:
            logger.info(f"Notification deduplicated for {recipient_id} on event {event_key}")
            return existing

    # Create the base notification
    notification = Notification(
        organization_id=organization_id,
        recipient_id=recipient_id,
        event_type=event_type,
        event_key=event_key,
        title=title,
        body=body,
        action_url=action_url
    )
    db.add(notification)
    db.flush() # Get the ID
    
    # Determine channels based on rule
    rule = db.query(NotificationRule).filter(
        NotificationRule.organization_id == organization_id,
        NotificationRule.event_type == event_type,
        NotificationRule.is_active == True
    ).first()
    
    channels = rule.channels if rule else ["IN_APP"]
    
    for channel in channels:
        delivery = NotificationDelivery(
            notification_id=notification.id,
            channel=channel,
            status="PENDING"
        )
        db.add(delivery)
        
        if channel == "IN_APP":
            delivery.status = "SENT" # IN_APP is instantaneous
            
    db.commit()
    return notification
