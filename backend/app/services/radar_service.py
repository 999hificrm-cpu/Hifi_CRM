from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models.audit import AuditLog, RadarEvent
from app.models.lead import Lead
from app.models.task import Task
from app.models.activity import Activity
from app.schemas.radar import RadarOverviewResponse, RadarOpportunity, AuditLogOut, RadarEventOut


def record_audit(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
):
    audit = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address
    )
    db.add(audit)
    db.commit()


def get_radar_overview(db: Session, organization_id: str, user_id: Optional[str] = None) -> RadarOverviewResponse:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. High value opportunities (Radar score >= 70, status OPEN)
    lead_query = db.query(Lead).filter(
        Lead.organization_id == organization_id,
        Lead.status == "OPEN",
        Lead.score >= 70
    )
    if user_id:
        # If user is specified and not admin, can filter to assigned
        lead_query = lead_query.filter((Lead.owner_id == user_id) | (Lead.owner_id == None))

    top_leads = lead_query.order_by(desc(Lead.score)).limit(6).all()

    radar_opps = []
    for l in top_leads:
        reason = "High engagement & decision maker on file" if l.score >= 85 else "Target ICP match & fresh signals"
        rec_action = "Call Decision Maker" if l.contact_phone else "Send tailored proposal email"
        radar_opps.append(RadarOpportunity(
            lead_id=l.id,
            title=l.title,
            company_name=l.company_name,
            score=l.score,
            reason=reason,
            recommended_action=rec_action,
            urgency="HIGH" if l.score >= 85 else "MEDIUM"
        ))

    # 2. Overdue follow-ups count
    overdue_count = db.query(Task).filter(
        Task.organization_id == organization_id,
        Task.status == "PENDING",
        Task.due_at != None,
        Task.due_at < now
    ).count()

    # 3. Stale leads (no activities in last 7 days)
    seven_days_ago = now - timedelta(days=7)
    # Simple calculation of open leads created > 7 days ago
    stale_count = db.query(Lead).filter(
        Lead.organization_id == organization_id,
        Lead.status == "OPEN",
        Lead.created_at < seven_days_ago
    ).count()

    # 4. Total active pipeline value
    total_val = db.query(func.sum(Lead.value)).filter(
        Lead.organization_id == organization_id,
        Lead.status == "OPEN"
    ).scalar() or 0.0

    # 5. Radar activity today
    act_today = db.query(Activity).filter(
        Activity.organization_id == organization_id,
        Activity.occurred_at >= today_start
    ).count()

    # 6. Data access anomalies (detect rapid contact views or export attempts)
    anomalies = []
    export_attempts = db.query(AuditLog).filter(
        AuditLog.organization_id == organization_id,
        AuditLog.action.ilike("%EXPORT%"),
        AuditLog.created_at >= (now - timedelta(hours=24))
    ).count()
    if export_attempts > 5:
        anomalies.append({
            "type": "HIGH_EXPORT_VOLUME",
            "severity": "WARNING",
            "message": f"{export_attempts} export attempts detected in the last 24 hours."
        })

    return RadarOverviewResponse(
        high_value_opportunities=radar_opps,
        overdue_followups_count=overdue_count,
        stale_leads_count=stale_count,
        total_active_pipeline_value=float(total_val),
        radar_activity_today=act_today,
        data_access_anomalies=anomalies
    )


def list_audit_logs(
    db: Session,
    organization_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
) -> List[AuditLogOut]:
    query = db.query(AuditLog)
    if organization_id:
        query = query.filter(AuditLog.organization_id == organization_id)
    logs = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit).all()

    return [
        AuditLogOut(
            id=log.id,
            organization_id=log.organization_id,
            user_id=log.user_id,
            user_name=log.user.full_name if (hasattr(log, "user") and log.user) else None,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            old_values=log.old_values,
            new_values=log.new_values,
            ip_address=log.ip_address,
            created_at=log.created_at
        )
        for log in logs
    ]
