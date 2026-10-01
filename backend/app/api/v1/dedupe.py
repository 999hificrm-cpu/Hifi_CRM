import logging
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from app.core.deps import get_db, get_current_user, get_tenant_id
from app.models.user import User
from app.models.lead import Lead
from app.models.activity import Activity
from app.models.task import Task
from app.models.dedupe import DedupeCandidate
from app.services.lead_service import serialize_lead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dedupe", tags=["Data Quality & Deduplication"])


class ResolveCandidateRequest(BaseModel):
    action: str  # MERGE, KEEP_SEPARATE, IGNORE


class DedupeCandidateOut(BaseModel):
    id: str
    match_confidence: Optional[float] = None
    match_basis: Optional[str] = None
    status: str
    lead_a: Optional[dict] = None
    lead_b: Optional[dict] = None


@router.get("/candidates")
def list_dedupe_candidates(
    status_filter: Optional[str] = "PENDING",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Lists deduplication candidate pairs for review by Organization Admin / Sales Manager.
    Never auto-merges; provides one-click resolution.
    """
    query = db.query(DedupeCandidate).filter(
        DedupeCandidate.organization_id == tenant_id
    )
    if status_filter:
        query = query.filter(DedupeCandidate.status == status_filter.upper())

    candidates = query.order_by(desc(DedupeCandidate.created_at)).offset(skip).limit(limit).all()

    result = []
    for c in candidates:
        lead_a = db.query(Lead).filter(Lead.id == c.lead_id_a).first()
        lead_b = db.query(Lead).filter(Lead.id == c.lead_id_b).first()
        
        result.append({
            "id": c.id,
            "match_confidence": float(c.match_confidence) if c.match_confidence else 1.0,
            "match_basis": c.match_basis,
            "status": c.status,
            "lead_a": serialize_lead(lead_a, current_user, db).dict() if lead_a else None,
            "lead_b": serialize_lead(lead_b, current_user, db).dict() if lead_b else None,
            "created_at": str(c.created_at) if c.created_at else None
        })

    return result


@router.post("/candidates/{id}/resolve")
def resolve_dedupe_candidate(
    id: str,
    data: ResolveCandidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    One-click resolution: MERGE, KEEP_SEPARATE, or IGNORE.
    If MERGE: merges Lead B into Lead A (re-points activities/tasks, marks Lead B ARCHIVED/MERGED).
    Preserves relational integrity and audit history without hard-deleting.
    """
    if not (current_user.is_org_admin or current_user.tenant_role in ("ORG_ADMIN", "SALES_MANAGER", "SUPER_ADMIN")):
        raise HTTPException(status_code=403, detail="Only Org Admins and Sales Managers can resolve duplicates")

    candidate = db.query(DedupeCandidate).filter(
        DedupeCandidate.id == id,
        DedupeCandidate.organization_id == tenant_id
    ).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Duplicate candidate not found")

    action = data.action.upper()
    if action not in ("MERGE", "KEEP_SEPARATE", "IGNORE"):
        raise HTTPException(status_code=400, detail="Invalid action. Use MERGE, KEEP_SEPARATE, or IGNORE")

    if action == "MERGE":
        lead_a = db.query(Lead).filter(Lead.id == candidate.lead_id_a).first()
        lead_b = db.query(Lead).filter(Lead.id == candidate.lead_id_b).first()

        if lead_a and lead_b:
            # Reassign all activities from lead_b to lead_a
            db.query(Activity).filter(Activity.lead_id == lead_b.id).update({"lead_id": lead_a.id})
            # Reassign pending tasks
            db.query(Task).filter(Task.lead_id == lead_b.id).update({"lead_id": lead_a.id})
            
            # Archive lead_b as merged duplicate
            lead_b.status = "ARCHIVED"
            tags = list(lead_b.tags or [])
            if "MERGED_DUPLICATE" not in tags:
                tags.append("MERGED_DUPLICATE")
                lead_b.tags = tags
            lead_b.notes = (lead_b.notes or "") + f"\n[Merged into Lead #{lead_a.id} by {current_user.full_name}]"

            # Create audit activity
            act = Activity(
                organization_id=tenant_id,
                lead_id=lead_a.id,
                user_id=current_user.id,
                activity_type="SYSTEM",
                subject="Duplicate Merged",
                description=f"Merged duplicate Lead #{lead_b.id} ('{lead_b.title}') into this record.",
                status="COMPLETED"
            )
            db.add(act)

        candidate.status = "MERGED"

    elif action == "KEEP_SEPARATE":
        candidate.status = "KEPT_SEPARATE"
    elif action == "IGNORE":
        candidate.status = "IGNORED"

    db.commit()
    return {"status": "success", "candidate_status": candidate.status}


@router.post("/run")
def trigger_dedupe_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Triggers an immediate data quality and deduplication scan for the organization.
    Detects exact phone/email duplicates and near matches, populating dedupe_candidates.
    """
    from app.tasks.daily_tasks import run_organization_dedupe_scan
    count = run_organization_dedupe_scan(tenant_id, db)
    return {"status": "completed", "candidates_detected": count}
