from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class AuditLogOut(BaseModel):
    id: str
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RadarEventOut(BaseModel):
    id: str
    organization_id: str
    actor_user_id: str
    actor_user_name: Optional[str] = None
    action: str
    entity_type: str
    entity_id: str
    ip_address: Optional[str] = None
    occurred_at: datetime

    class Config:
        from_attributes = True


class RadarOpportunity(BaseModel):
    lead_id: str
    title: str
    company_name: Optional[str] = None
    score: int
    reason: str
    recommended_action: str
    urgency: str  # HIGH, MEDIUM, LOW


class RadarOverviewResponse(BaseModel):
    high_value_opportunities: List[RadarOpportunity] = []
    overdue_followups_count: int = 0
    stale_leads_count: int = 0
    total_active_pipeline_value: float = 0.0
    radar_activity_today: int = 0
    data_access_anomalies: List[Dict[str, Any]] = []
