from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class CompanyCreate(BaseModel):
    name: str
    legal_name: Optional[str] = None
    domain: Optional[str] = None
    cin: Optional[str] = None
    gstin: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    postal_code: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None
    domain: Optional[str] = None
    cin: Optional[str] = None
    gstin: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    status: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class CompanyOut(BaseModel):
    id: str
    organization_id: str
    name: str
    legal_name: Optional[str] = None
    domain: Optional[str] = None
    cin: Optional[str] = None
    gstin: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str
    postal_code: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
