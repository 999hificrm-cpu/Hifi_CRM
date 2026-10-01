from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class GlobalContactOut(BaseModel):
    id: str
    registry_id: Optional[str] = None
    full_name: str
    designation: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    city: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


class GlobalCompanyCreate(BaseModel):
    legal_name: str
    id: Optional[str] = None  # Unique UUID from our side (auto-generated if empty)
    cin: Optional[str] = None  # Corporate Identification Number
    registration_number: Optional[str] = None  # Registration Number
    gst_number: Optional[str] = None  # GST Number
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None  # Pincode
    state: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None  # Company Contact Number
    country: Optional[str] = "India"
    industry: Optional[str] = None
    company_type: Optional[str] = "Private Limited"


class GlobalCompanyUpdate(BaseModel):
    legal_name: Optional[str] = None
    cin: Optional[str] = None
    registration_number: Optional[str] = None
    gst_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    state: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    company_type: Optional[str] = None
    status: Optional[str] = None


class GlobalCompanyOut(BaseModel):
    id: str
    registry_id: str  # CIN or identifier
    legal_name: str
    display_name: Optional[str] = None
    company_type: Optional[str] = None
    industry: Optional[str] = None
    cin: Optional[str] = None
    registration_number: Optional[str] = None
    gst_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str
    postal_code: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: str
    first_seen_at: datetime
    last_updated_at: datetime

    class Config:
        from_attributes = True


class GlobalPullRequest(BaseModel):
    global_company_ids: List[str]
    target_stage_id: Optional[str] = None
    target_owner_id: Optional[str] = None


class GlobalPullResponse(BaseModel):
    pulled_companies: int
    pulled_contacts: int
    created_leads: int
    remaining_quota: int


class LinkedPersonOut(BaseModel):
    id: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = None
    company_name: Optional[str] = None
    seniority: Optional[str] = None
    department: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    linkedin_url: Optional[str] = None
    status: str = "ACTIVE"
    is_primary: bool = True
    estimated_value: float = 0.0

    class Config:
        from_attributes = True


class CompanyWithPeopleOut(BaseModel):
    id: str
    registry_id: str
    legal_name: str
    display_name: Optional[str] = None
    company_type: Optional[str] = None
    industry: Optional[str] = None
    cin: Optional[str] = None
    registration_number: Optional[str] = None
    gst_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    postal_code: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: str = "ACTIVE"
    contacts_count: int = 0
    associated_people: List[LinkedPersonOut] = []
    people_count: int = 0


class GlobalIntelligenceResponse(BaseModel):
    total_companies: int
    total_people: int
    linked_people_count: int
    unlinked_people_count: int = 0
    companies_with_people_count: int
    direct_reach_percentage: float = 0.0
    total_market_turnover: Optional[float] = 0.0
    companies: List[CompanyWithPeopleOut]
    unlinked_people: List[LinkedPersonOut] = []
