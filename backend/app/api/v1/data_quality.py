from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.deps import get_db, get_current_user, get_tenant_id
from app.models.user import User
from app.models.data_quality import DataQualityIssue

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])

class DataQualityIssueOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    issue_type: str
    severity: str
    status: str
    details_json: dict

@router.get("/issues", response_model=List[DataQualityIssueOut])
def get_data_quality_issues(
    status_filter: Optional[str] = "OPEN",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get data quality issues for the current tenant.
    """
    if not current_user.is_org_admin:
         raise HTTPException(status_code=403, detail="Only Org Admins can view data quality issues")
         
    query = db.query(DataQualityIssue).filter(DataQualityIssue.organization_id == tenant_id)
    if status_filter:
        query = query.filter(DataQualityIssue.status == status_filter.upper())
        
    issues = query.offset(skip).limit(limit).all()
    
    return [
        DataQualityIssueOut(
            id=issue.id,
            entity_type=issue.entity_type,
            entity_id=issue.entity_id,
            issue_type=issue.issue_type,
            severity=issue.severity,
            status=issue.status,
            details_json=issue.details_json
        ) for issue in issues
    ]

@router.post("/scan")
def trigger_data_quality_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Triggers an immediate data quality scan.
    """
    if not current_user.is_org_admin:
         raise HTTPException(status_code=403, detail="Only Org Admins can trigger scans")
         
    from app.services.data_quality_service import scan_organization_data_quality
    count = scan_organization_data_quality(db, tenant_id)
    return {"status": "completed", "issues_detected": count}
