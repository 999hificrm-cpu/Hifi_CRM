from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.jobs import JobRun

router = APIRouter(prefix="/jobs", tags=["Job Monitor"])

class JobRunOut(BaseModel):
    id: str
    job_id: str
    job_type: str
    status: str
    attempt: int
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    error_message: Optional[str]

@router.get("/", response_model=List[JobRunOut])
def get_jobs(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all background jobs and their execution status. Super Admin only.
    """
    if current_user.tenant_role != "SUPER_ADMIN":
         raise HTTPException(status_code=403, detail="Only Super Admins can monitor jobs")
         
    query = db.query(JobRun)
    if status_filter:
        query = query.filter(JobRun.status == status_filter.upper())
        
    jobs = query.order_by(desc(JobRun.started_at)).offset(skip).limit(limit).all()
    
    return [
        JobRunOut(
            id=job.id,
            job_id=job.job_id,
            job_type=job.job_type,
            status=job.status,
            attempt=job.attempt,
            started_at=job.started_at,
            completed_at=job.completed_at,
            duration_seconds=job.duration_seconds,
            error_message=job.error_message
        ) for job in jobs
    ]

@router.get("/failed", response_model=List[JobRunOut])
def get_failed_jobs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all failed jobs.
    """
    if current_user.tenant_role != "SUPER_ADMIN":
         raise HTTPException(status_code=403, detail="Only Super Admins can monitor jobs")
         
    jobs = db.query(JobRun).filter(JobRun.status == "FAILED").order_by(desc(JobRun.started_at)).offset(skip).limit(limit).all()
    
    return [
        JobRunOut(
            id=job.id,
            job_id=job.job_id,
            job_type=job.job_type,
            status=job.status,
            attempt=job.attempt,
            started_at=job.started_at,
            completed_at=job.completed_at,
            duration_seconds=job.duration_seconds,
            error_message=job.error_message
        ) for job in jobs
    ]
