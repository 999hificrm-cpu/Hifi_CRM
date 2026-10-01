from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user, get_tenant_id, ensure_lead_access
from app.models.user import User
from app.models.lead import Lead
from app.models.audit import RadarEvent
from app.services.masking_service import should_mask_field

router = APIRouter(prefix="/leads", tags=["vCard Contacts"])


def _escape_vcard(value: str) -> str:
    """Escape RFC 2426 text fields and prevent line-injection in a .vcf file."""
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r", " ").replace("\n", "\\n")


@router.get("/{lead_id}/vcard", response_class=Response)
def get_lead_vcard(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == tenant_id,
        Lead.deleted_at.is_(None),
    ).first()

    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    # The same object-level authorization used by every lead route prevents
    # URL tampering across telecallers, delegations, and organizations.
    ensure_lead_access(db, lead, current_user, tenant_id)

    # Do not turn a contact download into a data-masking bypass.  Fields that
    # the current caller is not allowed to see are omitted rather than exposed.
    fn = lead.contact_name or lead.title or "Unknown Contact"
    org = lead.company_name or ""
    tel = "" if should_mask_field(db, tenant_id, current_user, "PHONE", lead.id) else (lead.contact_phone or "")
    email = "" if should_mask_field(db, tenant_id, current_user, "EMAIL", lead.id) else (lead.contact_email or "")
    
    # We include Product and Purpose in the NOTE field to give context
    notes = []
    if lead.product_service_name:
        notes.append(f"Product/Service: {lead.product_service_name}")
    if lead.purpose:
        notes.append(f"Purpose: {lead.purpose}")
    
    note_str = " | ".join(notes)

    vcard_lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{_escape_vcard(fn)}",
        f"N:{_escape_vcard(fn)};;;;",
    ]
    
    if org:
        vcard_lines.append(f"ORG:{_escape_vcard(org)}")
    if tel:
        vcard_lines.append(f"TEL;TYPE=CELL:{_escape_vcard(tel)}")
    if email:
        vcard_lines.append(f"EMAIL;TYPE=WORK:{_escape_vcard(email)}")
    if note_str:
        vcard_lines.append(f"NOTE:{_escape_vcard(note_str)}")
        
    vcard_lines.append("END:VCARD")
    vcard_content = "\r\n".join(vcard_lines)

    # Sanitize filename
    safe_fn = "".join([c for c in fn if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_")
    filename = f"{safe_fn or 'contact'}.vcf"

    db.add(RadarEvent(
        organization_id=tenant_id,
        actor_user_id=current_user.id,
        action="VCARD_DOWNLOAD",
        entity_type="LEAD",
        entity_id=lead.id,
        metadata_json={"phone_included": bool(tel), "email_included": bool(email)},
    ))
    db.commit()

    return Response(
        content=vcard_content,
        media_type="text/vcard",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        }
    )
