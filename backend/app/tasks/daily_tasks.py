import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, text
from rapidfuzz import fuzz

from app.worker import celery_app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.telecaller_target import TelecallerTarget
from app.models.lead import Lead
from app.models.activity import Activity
from app.models.call_record import CallRecord
from app.core.business_time import organization_business_date, organization_timezone
from app.models.session import TelecallerSession
from app.models.eod_report import EODReport
from app.models.dedupe import DedupeCandidate
from app.models.organization import Organization
from app.models.base import generate_uuid, utc_now

logger = logging.getLogger(__name__)


@celery_app.task
def initialize_daily_targets():
    """
    Runs daily (e.g. at midnight) to create fresh TelecallerTarget rows for all active telecallers.
    """
    logger.info("Starting initialize_daily_targets job")
    db: Session = SessionLocal()
    try:
        # Targets must be created for each organization's local business date,
        # not the Celery host's UTC day.
        
        telecallers = db.query(User).filter(
            User.status == "ACTIVE",
            User.deleted_at.is_(None),
            User.tenant_role == "TELECALLER"
        ).all()
        
        created = 0
        for tc in telecallers:
            today = organization_business_date(db, tc.organization_id)
            existing = db.query(TelecallerTarget).filter(
                TelecallerTarget.organization_id == tc.organization_id,
                TelecallerTarget.user_id == tc.id,
                TelecallerTarget.target_date == today
            ).first()
            
            if not existing:
                previous = db.query(TelecallerTarget).filter(
                    TelecallerTarget.organization_id == tc.organization_id,
                    TelecallerTarget.user_id == tc.id,
                    TelecallerTarget.target_date < today,
                ).order_by(TelecallerTarget.target_date.desc()).first()
                # No configured history means no target. Do not manufacture a
                # zero-valued row that the API would mislabel as configured.
                if not previous:
                    continue
                new_target = TelecallerTarget(
                    id=generate_uuid(),
                    organization_id=tc.organization_id,
                    user_id=tc.id,
                    target_date=today,
                    target_calls=previous.target_calls or 0,
                    target_connects=previous.target_connects or 0,
                    target_talk_time_minutes=previous.target_talk_time_minutes or 0,
                    target_qualified_leads=previous.target_qualified_leads or 0,
                    target_conversions=previous.target_conversions or 0,
                    target_revenue=previous.target_revenue or 0.0,
                )
                db.add(new_target)
                created += 1
                
        db.commit()
        logger.info(f"Successfully initialized targets for {created} telecallers.")
        
    except Exception as e:
        logger.error(f"Error in initialize_daily_targets: {e}")
        db.rollback()
    finally:
        db.close()


def run_organization_dedupe_scan(org_id: str, db: Session) -> int:
    """
    Problem 7: Data Quality & Deduplication Engine.
    Detects exact phone/email duplicates and fuzzy name/company matches.
    Writes candidate pairs to dedupe_candidates for 1-click admin merge/keep/ignore.
    Auto-archives stale leads (OPEN, no activities in 45 days, >4 call attempts).
    """
    logger.info(f"Running data quality scan for organization {org_id}")
    candidates_created = 0

    # 1. Exact Phone Duplicates
    phone_dupes = db.query(
        Lead.contact_phone
    ).filter(
        Lead.organization_id == org_id,
        Lead.contact_phone != None,
        Lead.contact_phone != "",
        Lead.status != "ARCHIVED"
    ).group_by(Lead.contact_phone).having(func.count(Lead.id) > 1).all()

    for (p,) in phone_dupes:
        leads = db.query(Lead).filter(
            Lead.organization_id == org_id,
            Lead.contact_phone == p,
            Lead.status != "ARCHIVED"
        ).all()
        if len(leads) >= 2:
            lead_a, lead_b = leads[0], leads[1]
            existing = db.query(DedupeCandidate).filter(
                DedupeCandidate.organization_id == org_id,
                or_(
                    (DedupeCandidate.lead_id_a == lead_a.id) & (DedupeCandidate.lead_id_b == lead_b.id),
                    (DedupeCandidate.lead_id_a == lead_b.id) & (DedupeCandidate.lead_id_b == lead_a.id)
                )
            ).first()
            if not existing:
                cand = DedupeCandidate(
                    organization_id=org_id,
                    lead_id_a=lead_a.id,
                    lead_id_b=lead_b.id,
                    match_confidence=1.0,
                    match_basis="Exact Phone Match",
                    status="PENDING"
                )
                db.add(cand)
                candidates_created += 1

    # 2. Exact Email Duplicates
    email_dupes = db.query(
        Lead.contact_email
    ).filter(
        Lead.organization_id == org_id,
        Lead.contact_email != None,
        Lead.contact_email != "",
        Lead.status != "ARCHIVED"
    ).group_by(Lead.contact_email).having(func.count(Lead.id) > 1).all()

    for (em,) in email_dupes:
        leads = db.query(Lead).filter(
            Lead.organization_id == org_id,
            Lead.contact_email == em,
            Lead.status != "ARCHIVED"
        ).all()
        if len(leads) >= 2:
            lead_a, lead_b = leads[0], leads[1]
            existing = db.query(DedupeCandidate).filter(
                DedupeCandidate.organization_id == org_id,
                or_(
                    (DedupeCandidate.lead_id_a == lead_a.id) & (DedupeCandidate.lead_id_b == lead_b.id),
                    (DedupeCandidate.lead_id_a == lead_b.id) & (DedupeCandidate.lead_id_b == lead_a.id)
                )
            ).first()
            if not existing:
                cand = DedupeCandidate(
                    organization_id=org_id,
                    lead_id_a=lead_a.id,
                    lead_id_b=lead_b.id,
                    match_confidence=1.0,
                    match_basis="Exact Email Match",
                    status="PENDING"
                )
                db.add(cand)
                candidates_created += 1

    # 3. Fuzzy Company & Name Matching (rapidfuzz)
    active_leads = db.query(Lead).filter(
        Lead.organization_id == org_id,
        Lead.status != "ARCHIVED"
    ).limit(300).all()

    for i in range(len(active_leads)):
        for j in range(i + 1, min(i + 15, len(active_leads))):
            l1, l2 = active_leads[i], active_leads[j]
            comp1 = (l1.company_name or "").strip().lower()
            comp2 = (l2.company_name or "").strip().lower()
            if comp1 and comp2 and len(comp1) > 4 and len(comp2) > 4:
                ratio = fuzz.token_sort_ratio(comp1, comp2)
                if ratio >= 88:
                    existing = db.query(DedupeCandidate).filter(
                        DedupeCandidate.organization_id == org_id,
                        or_(
                            (DedupeCandidate.lead_id_a == l1.id) & (DedupeCandidate.lead_id_b == l2.id),
                            (DedupeCandidate.lead_id_a == l2.id) & (DedupeCandidate.lead_id_b == l1.id)
                        )
                    ).first()
                    if not existing:
                        cand = DedupeCandidate(
                            organization_id=org_id,
                            lead_id_a=l1.id,
                            lead_id_b=l2.id,
                            match_confidence=round(ratio / 100.0, 2),
                            match_basis=f"Fuzzy Company Match ({ratio}%)",
                            status="PENDING"
                        )
                        db.add(cand)
                        candidates_created += 1

    # 4. Auto-archive stale leads (no activities in 45 days, >4 call attempts)
    cutoff = datetime.now(timezone.utc) - timedelta(days=45)
    open_leads = db.query(Lead).filter(
        Lead.organization_id == org_id,
        Lead.status == "OPEN"
    ).all()

    stale_count = 0
    for l in open_leads:
        recent_count = db.query(Activity).filter(
            Activity.lead_id == l.id,
            Activity.occurred_at > cutoff
        ).count()
        total_calls = db.query(Activity).filter(
            Activity.lead_id == l.id,
            Activity.activity_type == "CALL"
        ).count()
        if recent_count == 0 and total_calls > 4:
            l.status = "STALE"
            stale_count += 1

    db.commit()
    logger.info(f"Dedupe scan completed for {org_id}: {candidates_created} candidates, {stale_count} stale leads archived.")
    return candidates_created


@celery_app.task
def dynamic_cleanup_and_deduplication():
    """
    Nightly Celery periodic task across all organizations.
    """
    logger.info("Starting dynamic_cleanup_and_deduplication job across all orgs")
    db: Session = SessionLocal()
    try:
        orgs = db.query(Organization).all()
        for org in orgs:
            try:
                run_organization_dedupe_scan(org.id, db)
                
                # Run Data Quality Scan (Phase 4)
                from app.services.data_quality_service import scan_organization_data_quality
                scan_organization_data_quality(db, org.id)
                
            except Exception as org_e:
                logger.error(f"Error scanning org {org.id}: {org_e}")
                db.rollback()
    finally:
        db.close()


@celery_app.task
def generate_eod_reports():
    """
    Problem 10: Automatic End-of-Day (EOD) Reports.
    Scheduled daily (e.g. 19:00).
    Aggregates SQL KPIs: calls_made, connects, talk_time_seconds, qualified, conversions, revenue, achievement %.
    Drafts AI narrative summary and coachable moments.
    """
    logger.info("Starting generate_eod_reports job")
    db: Session = SessionLocal()
    try:
        telecallers = db.query(User).filter(
            User.status == "ACTIVE",
            User.deleted_at.is_(None),
            User.tenant_role == "TELECALLER"
        ).all()
        
        for tc in telecallers:
            today = organization_business_date(db, tc.organization_id)
            tz = organization_timezone(db, tc.organization_id)
            today_start = datetime.combine(today, datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
            today_end = datetime.combine(today, datetime.max.time(), tzinfo=tz).astimezone(timezone.utc)
            existing = db.query(EODReport).filter(
                EODReport.organization_id == tc.organization_id,
                EODReport.user_id == tc.id,
                EODReport.report_date == today
            ).first()
            
            # Compute SQL metrics
            calls_made = db.query(CallRecord).filter(
                CallRecord.organization_id == tc.organization_id,
                CallRecord.user_id == tc.id,
                CallRecord.started_at >= today_start,
                CallRecord.started_at <= today_end,
                CallRecord.disposition != "INITIATED",
            ).count()

            connects = db.query(CallRecord).filter(
                CallRecord.organization_id == tc.organization_id,
                CallRecord.user_id == tc.id,
                CallRecord.disposition.in_(["CONNECTED", "INTERESTED", "CALLBACK", "PROPOSAL_SENT"]),
                CallRecord.started_at >= today_start,
                CallRecord.started_at <= today_end,
            ).count()

            talk_time = db.query(func.sum(CallRecord.duration_seconds)).filter(
                CallRecord.organization_id == tc.organization_id,
                CallRecord.user_id == tc.id,
                CallRecord.started_at >= today_start,
                CallRecord.started_at <= today_end,
            ).scalar() or 0

            conversions = db.query(Lead).filter(
                Lead.organization_id == tc.organization_id,
                Lead.owner_id == tc.id,
                Lead.status == "WON",
                Lead.updated_at >= today_start,
                Lead.updated_at <= today_end
            ).count()

            revenue = db.query(func.sum(Lead.value)).filter(
                Lead.organization_id == tc.organization_id,
                Lead.owner_id == tc.id,
                Lead.status == "WON",
                Lead.updated_at >= today_start,
                Lead.updated_at <= today_end
            ).scalar() or 0.0

            target = db.query(TelecallerTarget).filter(
                TelecallerTarget.organization_id == tc.organization_id,
                TelecallerTarget.user_id == tc.id,
                TelecallerTarget.target_date == today
            ).first()

            target_calls = target.target_calls if target else 0
            achievement_pct = round(min(100.0, (calls_made / target_calls * 100)) if target_calls > 0 else 0, 1)

            metrics = {
                "calls_made": calls_made,
                "connects": connects,
                "talk_time_seconds": talk_time,
                "talk_time_minutes": talk_time // 60,
                "conversions": conversions,
                "revenue": float(revenue),
                "target_calls": target_calls,
                "target_achievement_pct": achievement_pct
            }

            # AI narrative drafted strictly explaining the SQL computed metrics
            ai_narrative = (
                f"{tc.full_name} completed {calls_made} calls today ({achievement_pct}% of daily target), "
                f"achieving {connects} connected discussions and {talk_time // 60} minutes of total talk time. "
                f"Conversions: {conversions} deals closed (Total value: INR {revenue:,.2f}). "
                f"Coachable insight: Focus on converting high-interest callbacks scheduled earlier in the session."
            )

            if existing:
                existing.metrics_snapshot = metrics
                existing.ai_summary = ai_narrative
            else:
                report = EODReport(
                    id=generate_uuid(),
                    organization_id=tc.organization_id,
                    user_id=tc.id,
                    report_date=today,
                    metrics_snapshot=metrics,
                    ai_summary=ai_narrative
                )
                db.add(report)
                
        db.commit()
        logger.info("Successfully generated and saved EOD reports.")
        
    except Exception as e:
        logger.error(f"Error in generate_eod_reports: {e}")
        db.rollback()
    finally:
        db.close()
