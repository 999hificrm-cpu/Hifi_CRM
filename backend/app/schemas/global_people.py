from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AssociatedCompanyItem(BaseModel):
    company_name: str
    designation: Optional[str] = None


class GlobalPersonCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = None  # Primary Role / Job Title
    company_name: Optional[str] = None  # Primary Company
    associated_companies: Optional[List[AssociatedCompanyItem]] = None
    industry: Optional[str] = None
    seniority: Optional[str] = None  # C-Level, VP, Director, Manager, Lead, Individual Contributor
    department: Optional[str] = None  # Sales, Marketing, Engineering, Operations, Finance, HR, Executive
    linkedin_url: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    estimated_value: Optional[float] = 0.0
    status: Optional[str] = "ACTIVE"
    source: Optional[str] = "MANUAL"
    notes: Optional[str] = None


class GlobalPersonUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = None
    company_name: Optional[str] = None
    associated_companies: Optional[List[AssociatedCompanyItem]] = None
    industry: Optional[str] = None
    seniority: Optional[str] = None
    department: Optional[str] = None
    linkedin_url: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    estimated_value: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class GlobalPersonOut(BaseModel):
    id: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = None
    company_name: Optional[str] = None
    associated_companies: Optional[List[Dict[str, Any]]] = None
    industry: Optional[str] = None
    seniority: Optional[str] = None
    department: Optional[str] = None
    linkedin_url: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str
    estimated_value: float = 0.0
    status: str
    source: str
    notes: Optional[str] = None
    first_seen_at: datetime
    last_updated_at: datetime

    class Config:
        from_attributes = True


class GlobalPeoplePullRequest(BaseModel):
    global_people_ids: List[str]
    target_organization_id: Optional[str] = None
    target_stage_id: Optional[str] = None
    target_owner_id: Optional[str] = None


class GlobalPeoplePullResponse(BaseModel):
    pulled_people: int
    created_contacts: int
    created_companies: int
    created_leads: int
    remaining_quota: Optional[int] = None
