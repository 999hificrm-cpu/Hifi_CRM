from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.schemas.pipeline import PipelineStageOut


class LeadStageHistoryOut(BaseModel):
    id: str
    lead_id: str
    from_stage_id: Optional[str] = None
    to_stage_id: str
    from_stage_name: Optional[str] = None
    to_stage_name: Optional[str] = None
    changed_by: Optional[str] = None
    changed_by_name: Optional[str] = None
    reason: Optional[str] = None
    duration_seconds: Optional[int] = 0
    created_at: datetime

    class Config:
        from_attributes = True


class LeadCreate(BaseModel):
    title: str
    company_id: Optional[str] = None
    contact_id: Optional[str] = None
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    pipeline_stage_id: Optional[str] = None  # If omitted, will resolve to default pipeline's first stage
    owner_id: Optional[str] = None
    source: Optional[str] = "MANUAL"
    priority: Optional[str] = "MEDIUM"
    score: Optional[int] = 50
    value: Optional[Decimal] = Decimal("0.00")
    currency: Optional[str] = "INR"
    description: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    product_service_id: Optional[str] = None
    product_service_name: Optional[str] = None
    purpose: Optional[str] = None
    segment: Optional[str] = None
    lead_type: Optional[str] = None


class LeadUpdate(BaseModel):
    title: Optional[str] = None
    company_id: Optional[str] = None
    contact_id: Optional[str] = None
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    owner_id: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    score: Optional[int] = None
    value: Optional[Decimal] = None
    currency: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    product_service_id: Optional[str] = None
    product_service_name: Optional[str] = None
    purpose: Optional[str] = None
    segment: Optional[str] = None
    lead_type: Optional[str] = None


class LeadStageChangeRequest(BaseModel):
    stage_id: str
    reason: Optional[str] = None


class LeadAssignRequest(BaseModel):
    owner_id: str


class LeadOut(BaseModel):
    id: str
    organization_id: str
    company_id: Optional[str] = None
    contact_id: Optional[str] = None
    pipeline_stage_id: str
    owner_id: Optional[str] = None
    title: str
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    source: str
    status: str
    priority: str
    score: int
    value: Optional[Decimal] = None
    currency: str
    description: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = []
    product_service_id: Optional[str] = None
    product_service_name: Optional[str] = None
    purpose: Optional[str] = None
    segment: Optional[str] = None
    lead_type: Optional[str] = None
    is_phone_masked: bool = False
    is_email_masked: bool = False
    stage: Optional[PipelineStageOut] = None
    owner_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
