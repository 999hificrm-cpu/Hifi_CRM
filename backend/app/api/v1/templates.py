from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from jinja2 import Environment, BaseLoader, TemplateSyntaxError
import logging

from app.core.deps import get_db, get_current_user, get_tenant_id, require_org_admin
from app.models.user import User
from app.models.template import Template
from app.models.lead import Lead

router = APIRouter(prefix="/templates", tags=["Templates"])
logger = logging.getLogger(__name__)

class TemplateCreate(BaseModel):
    name: str
    medium: str
    subject: Optional[str] = None
    body_template: str

class TemplateOut(BaseModel):
    id: str
    name: str
    medium: str
    subject: Optional[str] = None
    body_template: str

    class Config:
        from_attributes = True

class RenderRequest(BaseModel):
    lead_id: str

@router.post("", response_model=TemplateOut, dependencies=[Depends(require_org_admin)])
def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    # Validate Jinja template syntax
    try:
        env = Environment(loader=BaseLoader())
        env.from_string(data.body_template)
    except TemplateSyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Invalid template syntax: {str(e)}")

    template = Template(
        organization_id=tenant_id,
        name=data.name,
        medium=data.medium,
        subject=data.subject,
        body_template=data.body_template
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("", response_model=List[TemplateOut])
def list_templates(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    templates = db.query(Template).filter(Template.organization_id == tenant_id).all()
    return templates


@router.post("/{template_id}/render")
def render_template(
    template_id: str,
    data: RenderRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.organization_id == tenant_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    lead = db.query(Lead).filter(
        Lead.id == data.lead_id,
        Lead.organization_id == tenant_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    try:
        env = Environment(loader=BaseLoader())
        jinja_template = env.from_string(template.body_template)
        
        # Build context from lead
        context = {
            "lead": {
                "title": lead.title,
                "company_name": lead.company_name or "",
                "contact_name": lead.contact_name or "",
                "contact_email": lead.contact_email or "",
                "contact_phone": lead.contact_phone or ""
            }
        }
        
        rendered_body = jinja_template.render(context)
        return {"rendered": rendered_body}
    except Exception as e:
        logger.error(f"Template render error: {e}")
        raise HTTPException(status_code=500, detail="Error rendering template")
