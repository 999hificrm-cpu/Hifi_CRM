from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException, status

from app.models.lead import Lead
from app.models.lead_history import LeadStageHistory, LeadAssignment
from app.models.pipeline import PipelineStage
from app.models.company import Company
from app.models.contact import Contact
from app.models.user import User
from app.models.activity import Activity
from app.models.audit import AuditLog
from app.schemas.lead import LeadCreate, LeadUpdate, LeadOut, PipelineStageOut
from app.services.pipeline_service import get_stage_by_id, get_first_stage
from app.services.masking_service import should_mask_field, mask_phone_number, mask_email_address
from app.services.lead_qualification_service import resolve_segment
from app.core.business_time import organization_business_date


from app.models.product_service import ProductService

def create_lead(
    db: Session,
    organization_id: str,
    data: LeadCreate,
    creator_user: Optional[User] = None
) -> Lead:
    user_id = creator_user.id if creator_user else None

    owner_id = data.owner_id
    if owner_id:
        owner = db.query(User).filter(
            User.id == owner_id,
            User.organization_id == organization_id,
            User.tenant_role == "TELECALLER",
            User.status == "ACTIVE",
            User.deleted_at.is_(None),
        ).first()
        if not owner:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner must be an active telecaller in this organization")
    elif creator_user and creator_user.tenant_role == "TELECALLER":
        owner_id = creator_user.id

    # 1. Resolve pipeline stage
    if data.pipeline_stage_id:
        stage = get_stage_by_id(db, data.pipeline_stage_id, organization_id)
    else:
        stage = get_first_stage(db, organization_id)

    # 2. Resolve or sync Company
    comp_name = data.company_name
    company = None
    if data.company_id:
        company = db.query(Company).filter(
            Company.id == data.company_id,
            Company.organization_id == organization_id
        ).first()
        if company and not comp_name:
            comp_name = company.name

    # 3. Resolve or sync Contact
    from app.services.telephony_service import parse_and_format_phone
    contact = None
    c_name = data.contact_name
    c_email = data.contact_email
    c_phone, p_type, p_sms = parse_and_format_phone(data.contact_phone)
    if not c_phone:
        c_phone = data.contact_phone

    if data.contact_id:
        contact = db.query(Contact).filter(
            Contact.id == data.contact_id,
            Contact.organization_id == organization_id
        ).first()
        if contact:
            c_name = c_name or contact.full_name
            c_email = c_email or contact.email
            c_phone = c_phone or (parse_and_format_phone(contact.phone)[0] or contact.phone)
            if not company and contact.company_id:
                company = contact.company
                comp_name = comp_name or (company.name if company else None)

    # If contact name provided without contact_id, auto-link/create contact
    if not contact and c_name:
        from app.services.contact_service import get_or_create_contact
        contact, _ = get_or_create_contact(
            db=db,
            organization_id=organization_id,
            full_name=c_name,
            phone=c_phone,
            email=c_email,
            company_id=company.id if company else None,
            user_id=user_id
        )

    # 4. Compute status from stage
    lead_status = "OPEN"
    closed_at = None
    if stage.is_won:
        lead_status = "WON"
        closed_at = datetime.now(timezone.utc)
    elif stage.is_lost:
        lead_status = "LOST"
        closed_at = datetime.now(timezone.utc)

    # 4b. Resolve Product/Service Name
    product_service_name = data.product_service_name
    product_service_id = data.product_service_id
    if data.product_service_id:
        ps = db.query(ProductService).filter(
            ProductService.id == data.product_service_id,
            ProductService.organization_id == organization_id,
            ProductService.is_active.is_(True),
        ).first()
        if not ps:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product/Service not found in organization catalog")
        product_service_name = ps.name
    elif data.product_service_name:
        ps = db.query(ProductService).filter(
            ProductService.organization_id == organization_id,
            ProductService.name.ilike(data.product_service_name.strip()),
            ProductService.is_active.is_(True),
        ).first()
        if not ps:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product/Service not found in organization catalog")
        product_service_id = ps.id
        product_service_name = ps.name

    # 5. Create Lead
    lead = Lead(
        organization_id=organization_id,
        company_id=company.id if company else data.company_id,
        contact_id=contact.id if contact else data.contact_id,
        pipeline_stage_id=stage.id,
        owner_id=owner_id,
        title=data.title.strip(),
        company_name=comp_name,
        contact_name=c_name,
        contact_email=c_email.lower().strip() if c_email else None,
        contact_phone=c_phone.strip() if c_phone else None,
        source=data.source or "MANUAL",
        status=lead_status,
        priority=data.priority or "MEDIUM",
        score=data.score or 50,
        value=data.value or 0.00,
        currency=data.currency or "INR",
        description=data.description,
        notes=data.notes,
        tags=data.tags or [],
        product_service_id=product_service_id,
        product_service_name=product_service_name,
        purpose=data.purpose,
        segment=resolve_segment(data.segment, comp_name, c_email),
        lead_type=data.lead_type.strip().upper() if data.lead_type else None,
        created_by=user_id,
        closed_at=closed_at
    )
    db.add(lead)
    db.flush()

    # 6. Record Initial Stage History
    history = LeadStageHistory(
        organization_id=organization_id,
        lead_id=lead.id,
        from_stage_id=None,
        to_stage_id=stage.id,
        changed_by=user_id,
        reason="Initial lead creation",
        duration_seconds=0
    )
    db.add(history)

    # 7. Record Assignment if owner is assigned
    if lead.owner_id:
        assignment = LeadAssignment(
            organization_id=organization_id,
            lead_id=lead.id,
            user_id=lead.owner_id,
            assigned_by=user_id,
            is_primary=True
        )
        db.add(assignment)

    # 8. Record Activity
    activity = Activity(
        organization_id=organization_id,
        lead_id=lead.id,
        company_id=lead.company_id,
        contact_id=lead.contact_id,
        user_id=user_id or lead.owner_id,
        activity_type="SYSTEM",
        subject="Lead Created",
        description=f"Lead created in stage '{stage.name}' with priority '{lead.priority}'",
        status="COMPLETED"
    )
    db.add(activity)

    # 9. Audit Log
    audit = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        action="LEAD_CREATED",
        entity_type="LEAD",
        entity_id=lead.id,
        new_values={"title": lead.title, "stage": stage.name, "score": lead.score}
    )
    db.add(audit)

    db.commit()
    try:
        db.refresh(lead)
    except Exception:
        pass
    return lead


def change_lead_stage(
    db: Session,
    lead_id: str,
    to_stage_id: str,
    organization_id: str,
    actor_user: User,
    reason: Optional[str] = None,
    commit: bool = True,
) -> Lead:
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization_id
    ).with_for_update().first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    # This service is the lifecycle boundary, so non-list callers cannot bypass
    # the same object-level authorization enforced by lead endpoints.
    from app.core.deps import ensure_lead_access
    ensure_lead_access(db, lead, actor_user, organization_id)

    new_stage = get_stage_by_id(db, to_stage_id, organization_id)
    if lead.pipeline_stage_id == new_stage.id:
        return lead

    # Calculate duration in previous stage
    last_history = db.query(LeadStageHistory).filter(
        LeadStageHistory.lead_id == lead.id
    ).order_by(desc(LeadStageHistory.created_at)).first()

    duration_sec = 0
    now = datetime.now(timezone.utc)
    if last_history and last_history.created_at:
        # SQLite vs PostgreSQL timezone compatibility
        last_time = last_history.created_at
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)
        duration_sec = int((now - last_time).total_seconds())

    # Record Stage History
    history = LeadStageHistory(
        organization_id=organization_id,
        lead_id=lead.id,
        from_stage_id=lead.pipeline_stage_id,
        to_stage_id=new_stage.id,
        changed_by=actor_user.id,
        reason=reason or f"Moved to {new_stage.name}",
        duration_seconds=max(0, duration_sec)
    )
    db.add(history)

    # Update Lead Stage & Status
    old_stage_id = lead.pipeline_stage_id
    lead.pipeline_stage_id = new_stage.id

    if new_stage.is_won:
        lead.status = "WON"
        lead.closed_at = now
    elif new_stage.is_lost:
        lead.status = "LOST"
        lead.closed_at = now
    elif lead.status in ("WON", "LOST"):
        lead.status = "OPEN"
        lead.closed_at = None

    # Record Activity
    activity = Activity(
        organization_id=organization_id,
        lead_id=lead.id,
        user_id=actor_user.id,
        activity_type="STAGE_CHANGE",
        subject=f"Stage changed to {new_stage.name}",
        description=f"Moved from previous stage. Reason: {reason or 'Normal progression'}",
        status="COMPLETED"
    )
    db.add(activity)

    # Record Audit Log
    audit = AuditLog(
        organization_id=organization_id,
        user_id=actor_user.id,
        action="LEAD_STAGE_CHANGED",
        entity_type="LEAD",
        entity_id=lead.id,
        old_values={"stage_id": old_stage_id},
        new_values={"stage_id": new_stage.id, "stage_name": new_stage.name, "status": lead.status}
    )
    db.add(audit)

    if commit:
        db.commit()
        try:
            db.refresh(lead)
        except Exception:
            pass
    else:
        db.flush()
    return lead


def assign_lead(
    db: Session,
    lead_id: str,
    new_owner_id: str,
    organization_id: str,
    actor_user: User
) -> Lead:
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization_id
    ).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    new_owner = db.query(User).filter(
        User.id == new_owner_id,
        User.organization_id == organization_id,
        User.tenant_role == "TELECALLER",
        User.status == "ACTIVE",
        User.deleted_at.is_(None),
    ).first()
    if not new_owner:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee user not found in organization")

    # Safe assignment logic: Check if target user has an active shift
    from app.models.session import AttendanceSession
    from datetime import datetime, timezone
    today = organization_business_date(db, organization_id)
    active_shift = db.query(AttendanceSession).filter(
        AttendanceSession.organization_id == organization_id,
        AttendanceSession.user_id == new_owner.id,
        AttendanceSession.date == today,
        AttendanceSession.logout_at == None
    ).first()
    
    if not active_shift:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target user is not clocked in. Assignment rejected.")

    if lead.owner_id == new_owner.id:
        return lead
    lead.owner_id = new_owner.id

    # Mark active assignment unassigned
    db.query(LeadAssignment).filter(
        LeadAssignment.organization_id == organization_id,
        LeadAssignment.lead_id == lead.id,
        LeadAssignment.unassigned_at == None
    ).update({"unassigned_at": datetime.now(timezone.utc)})

    # Append new assignment
    assignment = LeadAssignment(
        organization_id=organization_id,
        lead_id=lead.id,
        user_id=new_owner.id,
        assigned_by=actor_user.id,
        is_primary=True
    )
    db.add(assignment)

    # Record Activity
    activity = Activity(
        organization_id=organization_id,
        lead_id=lead.id,
        user_id=actor_user.id,
        activity_type="ASSIGNMENT",
        subject=f"Lead assigned to {new_owner.full_name}",
        description=f"Reassigned by {actor_user.full_name}",
        status="COMPLETED"
    )
    db.add(activity)

    db.commit()
    try:
        db.refresh(lead)
    except Exception:
        pass
    return lead


def serialize_lead(lead: Lead, user: User, db: Session) -> LeadOut:
    mask_phone = should_mask_field(db, lead.organization_id, user, "PHONE", lead_id=lead.id)
    mask_email = should_mask_field(db, lead.organization_id, user, "EMAIL", lead_id=lead.id)

    phone_val = mask_phone_number(lead.contact_phone) if (mask_phone and lead.contact_phone) else lead.contact_phone
    email_val = mask_email_address(lead.contact_email) if (mask_email and lead.contact_email) else lead.contact_email

    stage_out = None
    if lead.stage:
        stage_out = PipelineStageOut(
            id=lead.stage.id,
            pipeline_id=lead.stage.pipeline_id,
            name=lead.stage.name,
            code=lead.stage.code,
            order_index=lead.stage.order_index,
            color=lead.stage.color,
            win_probability=lead.stage.win_probability,
            is_won=lead.stage.is_won,
            is_lost=lead.stage.is_lost
        )

    return LeadOut(
        id=lead.id,
        organization_id=lead.organization_id,
        company_id=lead.company_id,
        contact_id=lead.contact_id,
        pipeline_stage_id=lead.pipeline_stage_id,
        owner_id=lead.owner_id,
        title=lead.title,
        company_name=lead.company_name,
        contact_name=lead.contact_name,
        contact_email=email_val,
        contact_phone=phone_val,
        source=lead.source,
        status=lead.status,
        priority=lead.priority,
        score=lead.score,
        value=lead.value,
        currency=lead.currency,
        description=lead.description,
        notes=lead.notes,
        tags=lead.tags or [],
        product_service_id=lead.product_service_id,
        product_service_name=lead.product_service_name,
        purpose=lead.purpose,
        segment=lead.segment,
        lead_type=lead.lead_type,
        is_phone_masked=mask_phone,
        is_email_masked=mask_email,
        stage=stage_out,
        owner_name=lead.owner.full_name if lead.owner else None,
        created_at=lead.created_at,
        updated_at=lead.updated_at
    )
