from typing import List, Optional
from pydantic import BaseModel
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_

from app.core.deps import get_db, get_current_user, get_tenant_id, ensure_lead_access, require_org_admin
from app.models.user import User
from app.models.lead import Lead
from app.models.lead_history import LeadStageHistory
from app.models.lead_history import LeadAssignment
from app.models.activity import Activity
from app.models.product_service import ProductService
from app.models.audit import RadarEvent
from app.schemas.lead import (
    LeadCreate, LeadUpdate, LeadOut, LeadStageChangeRequest,
    LeadAssignRequest, LeadStageHistoryOut
)
from app.schemas.activity import ActivityOut
from app.services.lead_service import (
    create_lead, change_lead_stage, assign_lead, serialize_lead
)
from app.services.activity_service import get_lead_timeline
from app.services.email_service import get_configured_sender
from app.core.business_time import organization_business_date

router = APIRouter(prefix="/leads", tags=["Leads & Opportunities"])


@router.get("/", response_model=List[LeadOut])
def list_leads(
    status_filter: Optional[str] = Query(None, alias="status"),
    stage_id: Optional[str] = None,
    owner_id: Optional[str] = None,
    search: Optional[str] = None,
    priority: Optional[str] = None,
    segment: Optional[str] = None,
    lead_type: Optional[str] = None,
    min_score: Optional[int] = None,
    for_queue: bool = False,
    skip: int = 0,
    limit: int = 250,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    query = db.query(Lead).filter(Lead.organization_id == tenant_id, Lead.deleted_at.is_(None))


    # Telecallers strictly see only leads explicitly assigned to them by Org Admin, plus active delegations
    if current_user.tenant_role == "TELECALLER":
        from app.models.delegation import AbsenceDelegation
        from sqlalchemy import or_

        today_date = organization_business_date(db, tenant_id)
        delegators = db.query(AbsenceDelegation.absent_user_id).filter(
            AbsenceDelegation.organization_id == tenant_id,
            AbsenceDelegation.cover_user_id == current_user.id,
            AbsenceDelegation.start_date <= today_date,
            AbsenceDelegation.end_date >= today_date
        ).all()
        delegator_ids = [d[0] for d in delegators]

        if delegator_ids:
            query = query.filter(or_(Lead.owner_id == current_user.id, Lead.owner_id.in_(delegator_ids)))
        else:
            query = query.filter(Lead.owner_id == current_user.id)
    elif owner_id:
        query = query.filter(Lead.owner_id == owner_id)

    if status_filter:
        query = query.filter(Lead.status == status_filter.upper())
    if stage_id:
        query = query.filter(Lead.pipeline_stage_id == stage_id)
    if priority:
        query = query.filter(Lead.priority == priority.upper())
    if segment:
        requested_segment = segment.strip().upper()
        if requested_segment == "OTHER":
            # Includes legacy leads that pre-date the segment field.
            query = query.filter(
                or_(
                    Lead.segment.is_(None),
                    ~func.upper(Lead.segment).in_(("B2B", "B2C")),
                )
            )
        elif requested_segment in ("B2B", "B2C"):
            query = query.filter(func.upper(Lead.segment) == requested_segment)
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="segment must be one of B2B, B2C, or OTHER",
            )
    if lead_type:
        query = query.filter(Lead.lead_type == lead_type.upper())
    if min_score:
        query = query.filter(Lead.score >= min_score)
    if search:
        s = f"%{search}%"
        query = query.filter(
            (Lead.title.ilike(s)) |
            (Lead.company_name.ilike(s)) |
            (Lead.contact_name.ilike(s)) |
            (Lead.contact_email.ilike(s)) |
            (Lead.contact_phone.ilike(s))
        )

    if for_queue:
        # Priority for the calling queue:
        # 1. Hot / Urgent priority
        # 2. Leads with pending tasks
        # 3. High Score
        # 4. Oldest untouched leads
        leads = query.order_by(
            desc(Lead.priority == "URGENT"),
            desc(Lead.priority == "HIGH"),
            desc(Lead.score),
            Lead.updated_at
        ).offset(skip).limit(limit).all()
    else:
        leads = query.order_by(desc(Lead.created_at)).offset(skip).limit(limit).all()
        
    return [serialize_lead(l, current_user, db) for l in leads]


@router.post("/", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def create_new_lead(
    data: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    try:
        lead = create_lead(db, tenant_id, data, current_user)
    except ValueError as exc:
        # Segment values are part of the API contract.  Do not turn a bad
        # client filter/classification into an internal-server error.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return serialize_lead(lead, current_user, db)

class BatchAssignRequest(BaseModel):
    lead_ids: List[str]
    telecaller_id: str


@router.get("/available-for-assignment", response_model=List[LeadOut])
def get_leads_available_for_assignment(
    telecaller_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    if current_user.tenant_role not in ["ORG_ADMIN", "SALES_MANAGER", "SUPER_ADMIN"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        
    query = db.query(Lead).filter(
        Lead.organization_id == tenant_id,
        or_(
            Lead.owner_id.is_(None), 
            Lead.owner_id == telecaller_id,
            Lead.owner.has(User.tenant_role != "TELECALLER")
        ),
        Lead.status.notin_(["WON", "LOST", "ARCHIVED", "REJECTED"]),
        Lead.deleted_at.is_(None)
    )
    
    leads = query.order_by(Lead.created_at.desc()).limit(1000).all()
    return [serialize_lead(l, current_user, db) for l in leads]

@router.post("/batch-assign")
def batch_assign_leads(
    data: BatchAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Assigns multiple leads (e.g. 5, 20, 50) to a specific Telecaller in one transaction.
    """
    if not (current_user.is_org_admin or current_user.is_super_admin or current_user.tenant_role in ("ORG_ADMIN", "SALES_MANAGER")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Organization Admins can assign leads to telecallers")

    # Verify target telecaller exists in this organization
    telecaller = db.query(User).filter(
        User.id == data.telecaller_id,
        User.organization_id == tenant_id,
        User.tenant_role == "TELECALLER",
        User.status == "ACTIVE",
        User.deleted_at.is_(None),
    ).first()
    if not telecaller:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target telecaller not found in this organization")

    # Safe assignment logic: Check if telecaller has an active shift
    from app.models.session import AttendanceSession
    from datetime import datetime, timezone
    today = organization_business_date(db, tenant_id)
    active_shift = db.query(AttendanceSession).filter(
        AttendanceSession.organization_id == tenant_id,
        AttendanceSession.user_id == telecaller.id,
        AttendanceSession.date == today,
        AttendanceSession.logout_at == None
    ).first()
    
    if not active_shift:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target telecaller is not clocked in. Assignment rejected.")

    requested_ids = list(dict.fromkeys(data.lead_ids))
    if not requested_ids:
        raise HTTPException(status_code=422, detail="At least one lead ID is required")
    leads = db.query(Lead).filter(
        Lead.id.in_(requested_ids),
        Lead.organization_id == tenant_id,
        or_(
            Lead.owner_id.is_(None),
            Lead.owner.has(User.tenant_role != "TELECALLER")
        ),
        Lead.deleted_at.is_(None),
        Lead.status.notin_(["WON", "LOST", "ARCHIVED", "REJECTED"]),
    ).with_for_update().all()

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    for lead in leads:
        db.query(LeadAssignment).filter(
            LeadAssignment.organization_id == tenant_id,
            LeadAssignment.lead_id == lead.id,
            LeadAssignment.unassigned_at.is_(None)
        ).update({"unassigned_at": now}, synchronize_session=False)

        lead.owner_id = telecaller.id
        db.add(LeadAssignment(
            organization_id=tenant_id,
            lead_id=lead.id,
            user_id=telecaller.id,
            assigned_by=current_user.id,
            is_primary=True,
        ))
        activity = Activity(
            organization_id=tenant_id,
            lead_id=lead.id,
            user_id=current_user.id,
            activity_type="ASSIGNMENT",
            subject=f"Assigned to {telecaller.full_name}",
            description=f"Assigned by Org Admin {current_user.full_name} for calling queue."
        )
        db.add(activity)

    db.commit()
    return {
        "updated_count": len(leads),
        "skipped_count": len(requested_ids) - len(leads),
        "telecaller_id": telecaller.id,
        "telecaller_name": telecaller.full_name,
        "message": f"Assigned {len(leads)} unowned leads to {telecaller.full_name}; skipped {len(requested_ids) - len(leads)} already-owned, missing, or ineligible leads"
    }


class BulkReassignRequest(BaseModel):
    from_user_id: str
    to_user_id: str
    reason: Optional[str] = None


@router.patch("/bulk-reassign")
def bulk_reassign_leads(
    data: BulkReassignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Problem 8: Permanent handover fallback.
    Reassigns all OPEN leads from an absent user to another user in one transaction,
    writing an audit activity row per lead.
    """
    if not (current_user.is_org_admin or current_user.tenant_role in ("ORG_ADMIN", "SALES_MANAGER") or current_user.is_super_admin):
        raise HTTPException(status_code=403, detail="Only managers can perform bulk reassignment")

    to_user = db.query(User).filter(
        User.id == data.to_user_id,
        User.organization_id == tenant_id,
        User.tenant_role == "TELECALLER",
        User.status == "ACTIVE",
        User.deleted_at.is_(None),
    ).first()
    if not to_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    # Safe assignment logic: Check if target user has an active shift
    from app.models.session import AttendanceSession
    from datetime import datetime, timezone
    today = organization_business_date(db, tenant_id)
    active_shift = db.query(AttendanceSession).filter(
        AttendanceSession.organization_id == tenant_id,
        AttendanceSession.user_id == to_user.id,
        AttendanceSession.date == today,
        AttendanceSession.logout_at == None
    ).first()
    
    if not active_shift:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target user is not clocked in. Assignment rejected.")

    from_user = db.query(User.id).filter(
        User.id == data.from_user_id,
        User.organization_id == tenant_id,
    ).first()
    if not from_user:
        raise HTTPException(status_code=404, detail="Source user not found")

    leads = db.query(Lead).filter(
        Lead.organization_id == tenant_id,
        Lead.owner_id == data.from_user_id,
        Lead.status != "ARCHIVED"
    ).with_for_update().all()

    count = 0
    for lead in leads:
        db.query(LeadAssignment).filter(
            LeadAssignment.organization_id == tenant_id,
            LeadAssignment.lead_id == lead.id,
            LeadAssignment.unassigned_at.is_(None),
        ).update({LeadAssignment.unassigned_at: datetime.now(timezone.utc)}, synchronize_session=False)
        lead.owner_id = to_user.id
        db.add(LeadAssignment(
            organization_id=tenant_id,
            lead_id=lead.id,
            user_id=to_user.id,
            assigned_by=current_user.id,
            is_primary=True,
        ))
        act = Activity(
            organization_id=tenant_id,
            lead_id=lead.id,
            user_id=current_user.id,
            activity_type="ASSIGNMENT",
            subject=f"Bulk Reassigned to {to_user.full_name}",
            description=data.reason or f"Bulk permanent handover by {current_user.full_name}"
        )
        db.add(act)
        count += 1

    db.commit()
    return {"status": "success", "reassigned_count": count, "to_user": to_user.full_name}


class PreCallContextOut(BaseModel):
    lead: LeadOut
    timeline: List[ActivityOut]
    stage_history: List[LeadStageHistoryOut]
    ai_summary: Optional[dict] = None
    ai_next_action: Optional[dict] = None



@router.get("/{id}", response_model=LeadOut)
def get_lead_detail(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    lead = db.query(Lead).filter(
        Lead.id == id,
        Lead.organization_id == tenant_id,
        Lead.deleted_at.is_(None)
    ).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    ensure_lead_access(db, lead, current_user, tenant_id)

    # Record contact view in radar
    radar_event = RadarEvent(
        organization_id=tenant_id,
        actor_user_id=current_user.id,
        action="CONTACT_VIEW",
        entity_type="LEAD",
        entity_id=lead.id,
        ip_address=request.client.host if request.client else None
    )
    db.add(radar_event)
    db.commit()

    return serialize_lead(lead, current_user, db)


@router.delete("/{id}")
def delete_lead(
    id: str,
    reason: Optional[str] = "Deleted by user",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """Soft-deletes a lead and sends it to the platform Recycle Bin (Problem #10)."""
    lead = db.query(Lead).filter(
        Lead.id == id,
        Lead.organization_id == tenant_id,
        Lead.deleted_at.is_(None)
    ).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    ensure_lead_access(db, lead, current_user, tenant_id)

    from datetime import datetime, timezone
    lead.deleted_at = datetime.now(timezone.utc)
    lead.deleted_by = current_user.id
    lead.deletion_reason = reason
    db.commit()

    from app.services.audit_service import audit_service
    audit_service.record(
        db=db,
        action="LEAD_DELETED",
        entity_type="LEAD",
        entity_id=lead.id,
        actor_user_id=current_user.id,
        organization_id=tenant_id,
        old_values={"title": lead.title, "company_name": lead.company_name},
        new_values={"deleted_at": lead.deleted_at.isoformat()},
        reason=reason
    )

    return {"success": True, "message": "Lead moved to Recycle Bin"}



@router.patch("/{id}", response_model=LeadOut)
def update_lead(
    id: str,
    data: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    lead = db.query(Lead).filter(
        Lead.id == id,
        Lead.organization_id == tenant_id
    ).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    ensure_lead_access(db, lead, current_user, tenant_id)

    if data.title:
        lead.title = data.title.strip()
    if data.company_name:
        lead.company_name = data.company_name.strip()
    if data.contact_name:
        lead.contact_name = data.contact_name.strip()
    if data.contact_email is not None:
        lead.contact_email = data.contact_email.lower().strip() if data.contact_email else None
    if data.contact_phone is not None:
        lead.contact_phone = data.contact_phone.strip() if data.contact_phone else None
    if data.status is not None and data.status.upper() != lead.status:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Lead status is controlled by pipeline stage transitions; use POST /leads/{id}/stage",
        )
    if data.priority:
        lead.priority = data.priority.upper()
    if data.score is not None:
        lead.score = data.score
    if data.value is not None:
        lead.value = data.value
    if data.description is not None:
        lead.description = data.description
    if data.notes is not None:
        lead.notes = data.notes
    if data.tags is not None:
        lead.tags = data.tags
    if "product_service_id" in data.model_fields_set:
        if data.product_service_id is None:
            lead.product_service_id = None
            lead.product_service_name = None
        else:
            product_service = db.query(ProductService).filter(
                ProductService.id == data.product_service_id,
                ProductService.organization_id == tenant_id,
                ProductService.is_active.is_(True),
            ).first()
            if not product_service:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active Product/Service not found in organization")
            lead.product_service_id = product_service.id
            lead.product_service_name = product_service.name
    elif data.product_service_name is not None:
        product_service = db.query(ProductService).filter(
            ProductService.organization_id == tenant_id,
            ProductService.name.ilike(data.product_service_name.strip()),
            ProductService.is_active.is_(True),
        ).first()
        if not product_service:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product/Service not found in organization catalog")
        lead.product_service_id = product_service.id
        lead.product_service_name = product_service.name
    if data.purpose is not None:
        lead.purpose = data.purpose
    if data.segment is not None:
        from app.services.lead_qualification_service import normalize_segment
        try:
            lead.segment = normalize_segment(data.segment)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if data.lead_type is not None:
        lead.lead_type = data.lead_type.strip().upper() or None

    db.commit()
    try:
        db.refresh(lead)
    except Exception:
        pass
    return serialize_lead(lead, current_user, db)


@router.post("/{id}/stage", response_model=LeadOut)
def update_stage(
    id: str,
    data: LeadStageChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    lead = change_lead_stage(db, id, data.stage_id, tenant_id, current_user, data.reason)
    return serialize_lead(lead, current_user, db)


@router.post("/{id}/assign", response_model=LeadOut)
def reassign_lead(
    id: str,
    data: LeadAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
    tenant_id: str = Depends(get_tenant_id)
):
    lead = assign_lead(db, id, data.owner_id, tenant_id, current_user)
    return serialize_lead(lead, current_user, db)


@router.get("/{id}/pre-call-context", response_model=PreCallContextOut)
def get_pre_call_context(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Eagerly load full context, timeline, stage history, and latest AI insights
    for the telecaller to review before/during a call.
    """
    lead = db.query(Lead).filter(
        Lead.id == id,
        Lead.organization_id == tenant_id
    ).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    ensure_lead_access(db, lead, current_user, tenant_id)
        
    timeline = get_lead_timeline(db, id, tenant_id)
    
    sh_list = db.query(LeadStageHistory).filter(
        LeadStageHistory.lead_id == id,
        LeadStageHistory.organization_id == tenant_id
    ).order_by(desc(LeadStageHistory.created_at)).all()
    
    stage_history = [
        LeadStageHistoryOut(
            id=h.id,
            lead_id=h.lead_id,
            from_stage_id=h.from_stage_id,
            to_stage_id=h.to_stage_id,
            from_stage_name=h.from_stage.name if h.from_stage else None,
            to_stage_name=h.to_stage.name if h.to_stage else None,
            changed_by=h.changed_by,
            changed_by_name=h.user.full_name if h.user else None,
            reason=h.reason,
            duration_seconds=h.duration_seconds or 0,
            created_at=h.created_at
        )
        for h in sh_list
    ]

    # Fetch latest AI Insights if available
    from app.models.ai import AIInsight
    ai_summary_insight = db.query(AIInsight).filter(
        AIInsight.entity_type == "LEAD",
        AIInsight.entity_id == id,
        AIInsight.insight_type == "SUMMARY"
    ).order_by(desc(AIInsight.created_at)).first()
    
    ai_action_insight = db.query(AIInsight).filter(
        AIInsight.entity_type == "LEAD",
        AIInsight.entity_id == id,
        AIInsight.insight_type == "NEXT_ACTION"
    ).order_by(desc(AIInsight.created_at)).first()
    
    return PreCallContextOut(
        lead=serialize_lead(lead, current_user, db),
        timeline=timeline,
        stage_history=stage_history,
        ai_summary=ai_summary_insight.output_data if hasattr(ai_summary_insight, "output_data") else (ai_summary_insight.metadata_json if ai_summary_insight else None),
        ai_next_action=ai_action_insight.output_data if hasattr(ai_action_insight, "output_data") else (ai_action_insight.metadata_json if ai_action_insight else None)
    )


@router.get("/{id}/timeline", response_model=List[ActivityOut])
def get_timeline(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    lead = db.query(Lead).filter(Lead.id == id, Lead.organization_id == tenant_id, Lead.deleted_at.is_(None)).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    ensure_lead_access(db, lead, current_user, tenant_id)
    return get_lead_timeline(db, id, tenant_id)


@router.get("/{id}/stage-history", response_model=List[LeadStageHistoryOut])
def get_stage_history(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    lead = db.query(Lead).filter(Lead.id == id, Lead.organization_id == tenant_id, Lead.deleted_at.is_(None)).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    ensure_lead_access(db, lead, current_user, tenant_id)
    history = db.query(LeadStageHistory).filter(
        LeadStageHistory.lead_id == id,
        LeadStageHistory.organization_id == tenant_id
    ).order_by(desc(LeadStageHistory.created_at)).all()

    return [
        LeadStageHistoryOut(
            id=h.id,
            lead_id=h.lead_id,
            from_stage_id=h.from_stage_id,
            to_stage_id=h.to_stage_id,
            from_stage_name=h.from_stage.name if h.from_stage else None,
            to_stage_name=h.to_stage.name if h.to_stage else None,
            changed_by=h.changed_by,
            changed_by_name=h.user.full_name if h.user else None,
            reason=h.reason,
            duration_seconds=h.duration_seconds or 0,
            created_at=h.created_at
        )
        for h in history
    ]


class LeadActionResponse(BaseModel):
    status: str
    action_type: str
    lead_id: str
    gmail_url: Optional[str] = None
    whatsapp_url: Optional[str] = None
    tel_url: Optional[str] = None
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    message: Optional[str] = None


@router.post("/{id}/action/{action_type}", response_model=LeadActionResponse)
def trigger_lead_action(
    id: str,
    action_type: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    lead = db.query(Lead).filter(
        Lead.id == id,
        Lead.organization_id == tenant_id
    ).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    ensure_lead_access(db, lead, current_user, tenant_id)

    action_clean = action_type.lower()

    # Record auditable Radar event
    radar_event = RadarEvent(
        organization_id=tenant_id,
        actor_user_id=current_user.id,
        action=f"{action_clean.upper()}_TRIGGERED",
        entity_type="LEAD",
        entity_id=lead.id,
        ip_address=request.client.host if request.client else None
    )
    db.add(radar_event)
    db.commit()

    if action_clean in ("email", "mail"):
        target_email = (lead.contact_email or "").strip()
        if not target_email:
            raise HTTPException(status_code=400, detail="Lead does not have a recipient contact email address configured.")
        
        # Resolve configured authorized sender identity (supports Send-As / Workspace)
        configured_name, default_configured_email = get_configured_sender()
        authorized_sender = None
        if current_user.organization and current_user.organization.settings:
            authorized_sender = current_user.organization.settings.get("authorized_sender_email")
        if not authorized_sender:
            authorized_sender = default_configured_email or current_user.email

        subject = f"Regarding {lead.title} - {lead.company_name or 'Jarvis CRM'}"
        body = f"Hello {lead.contact_name or 'there'},\n\nI am reaching out regarding {lead.title}.\n\nBest regards,\n{current_user.full_name}"
        
        params = urllib.parse.urlencode({
            "view": "cm",
            "fs": "1",
            "tf": "cm",
            "to": target_email,
            "authuser": authorized_sender,
            "su": subject,
            "body": body
        })
        gmail_url = f"https://mail.google.com/mail/u/{urllib.parse.quote(authorized_sender)}/?{params}"
        return LeadActionResponse(
            status="success",
            action_type="email",
            lead_id=lead.id,
            gmail_url=gmail_url,
            recipient_email=target_email,
            message=f"Gmail composer link generated for authorized sender {authorized_sender}"
        )

    elif action_clean == "whatsapp":
        phone = lead.contact_phone or ""
        clean_digits = "".join([c for c in phone if c.isdigit()])
        text = f"Hello {lead.contact_name or ''}, reaching out regarding {lead.title} from {lead.company_name or 'our team'}."
        encoded_text = urllib.parse.quote(text)
        whatsapp_url = f"https://api.whatsapp.com/send?phone={clean_digits}&text={encoded_text}"
        return LeadActionResponse(
            status="success",
            action_type="whatsapp",
            lead_id=lead.id,
            whatsapp_url=whatsapp_url,
            recipient_phone=clean_digits,
            message="WhatsApp proxy dispatch ready"
        )

    elif action_clean == "call":
        phone = lead.contact_phone or ""
        clean_digits = "".join([c for c in phone if c.isdigit() or c == "+"])
        tel_url = f"tel:{clean_digits}" if clean_digits else None
        return LeadActionResponse(
            status="success",
            action_type="call",
            lead_id=lead.id,
            tel_url=tel_url,
            recipient_phone=lead.contact_phone,
            message="VoIP outbound call connection initialized"
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {action_type}")


class SendLeadEmailRequest(BaseModel):
    subject: str
    body: str
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    to_email: Optional[str] = None
    reply_to: Optional[str] = None


@router.post("/{lead_id}/send-email")
def dispatch_lead_email(
    lead_id: str,
    payload: SendLeadEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == tenant_id
    ).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    target_to = (payload.to_email or lead.contact_email or "").strip()
    if not target_to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recipient email address is missing")

    from app.services.email_service import send_lead_email, get_configured_sender
    auth_name, auth_email = get_configured_sender()

    # User/agent who is sending:
    agent_name = (current_user.full_name or payload.from_name or auth_name).strip()
    agent_email = (current_user.email or payload.from_email or auth_email).strip()
    
    # Reply-To routes replies directly to the agent/user
    reply_to_email = (payload.reply_to or agent_email or auth_email).strip()

    # Guard: Ensure To and From are distinct addresses
    if target_to.lower() == auth_email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Recipient email ({target_to}) cannot be identical to the system sender email ({auth_email}). A lead must have a distinct recipient address."
        )

    try:
        result = send_lead_email(
            to_email=target_to,
            from_email=auth_email,
            from_name=agent_name,
            reply_to=reply_to_email,
            subject=payload.subject,
            body=payload.body
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch email: {str(e)}")

    activity = Activity(
        organization_id=tenant_id,
        lead_id=lead.id,
        company_id=lead.company_id,
        contact_id=lead.contact_id,
        user_id=current_user.id,
        activity_type="EMAIL",
        subject=payload.subject or "Email Sent",
        description=f"From: {result['from_name']} <{result['from_email']}>\nTo: {result['to_email']}\nReply-To: {result['reply_to']}\n\n{payload.body}",
        status="COMPLETED"
    )
    db.add(activity)

    radar_event = RadarEvent(
        organization_id=tenant_id,
        actor_user_id=current_user.id,
        action="EMAIL_DISPATCHED",
        entity_type="LEAD",
        entity_id=lead.id
    )
    db.add(radar_event)
    db.commit()

    return {
        "status": "success",
        "message": f"Email successfully dispatched to {target_to} from {result['from_name']} <{result['from_email']}>",
        "result": result
    }
