from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ImportPreviewResponse(BaseModel):
    detected_headers: List[str]
    headers: Optional[List[str]] = None
    sample_rows: List[Dict[str, Any]]
    preview_rows: Optional[List[Dict[str, Any]]] = None
    suggested_mappings: Dict[str, str]  # file_column -> system_field
    total_detected_rows: int
    total_rows_estimate: Optional[int] = None
    file_path: str
    file_name: str
    file_type: str


class ImportJobExecuteRequest(BaseModel):
    file_path: str
    file_name: str
    file_type: str
    job_type: str = "TENANT_LEADS"  # TENANT_LEADS, GLOBAL_COMPANIES, GLOBAL_CONTACTS
    column_mapping: Dict[str, str]  # file_column -> system_field
    target_stage_id: Optional[str] = None
    target_owner_id: Optional[str] = None
    default_product_service_id: Optional[str] = None


class ImportRowErrorOut(BaseModel):
    id: str
    job_id: str
    row_number: int
    raw_data: Dict[str, Any]
    error_code: str
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ImportJobOut(BaseModel):
    id: str
    organization_id: Optional[str] = None
    uploaded_by: str
    uploader_name: Optional[str] = None
    job_type: str
    file_name: str
    file_type: str
    total_rows: int = 0
    processed_rows: int = 0
    successful_rows: int = 0
    duplicate_rows: int = 0
    error_rows: int = 0
    status: str = "PENDING"
    column_mapping: Dict[str, Any] = {}
    error_summary: Dict[str, Any] = {}
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
