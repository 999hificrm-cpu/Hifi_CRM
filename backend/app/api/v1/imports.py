import os
import uuid
import logging
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.deps import get_db, get_current_user, get_tenant_id, get_optional_tenant_id
from app.models.user import User
from app.models.import_job import ImportJob, ImportRowError
from app.models.base import utc_now
from app.schemas.import_job import (
    ImportPreviewResponse, ImportJobExecuteRequest, ImportJobOut, ImportRowErrorOut
)
from app.services.import_service import preview_import_file, execute_import_job
from app.tasks.import_tasks import run_import_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/imports", tags=["Import Ingestion Engine"])

# Ensure upload directory exists
os.makedirs(settings.STORAGE_LOCAL_DIR, exist_ok=True)


# Background runner logic moved to app.tasks.import_tasks



ALLOWED_TABULAR_EXTENSIONS = (".csv", ".xls", ".xlsx", ".xlsb", ".xlsm", ".parquet", ".json")


def _can_manage_imports(user: User) -> bool:
    return bool(
        user.is_super_admin
        or user.is_data_entry
        or user.tenant_role in ("ORG_ADMIN", "SALES_MANAGER")
    )


def _user_upload_dir(user: User) -> Path:
    root = Path(settings.STORAGE_LOCAL_DIR).resolve()
    directory = (root / user.id).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _resolve_user_upload(file_path: str, user: User) -> str:
    candidate = Path(file_path).resolve()
    user_root = _user_upload_dir(user)
    if not candidate.is_relative_to(user_root) or not candidate.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uploaded file not found")
    return str(candidate)


class ValidateImportRequest(BaseModel):
    file_path: str
    file_type: str
    column_mapping: dict


class AssignImportRequest(BaseModel):
    strategy: str = "ROUND_ROBIN"  # ROUND_ROBIN or CAPACITY
    telecaller_ids: Optional[List[str]] = None


@router.post("/upload", response_model=ImportPreviewResponse)
async def upload_import_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    # RBAC: Telecallers must never upload or touch import files
    if not _can_manage_imports(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telecallers do not have data import authorization. Only ORG Admin or Sales Manager can upload datasets."
        )

    # Strictly validate tabular extensions
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if ext not in ALLOWED_TABULAR_EXTENSIONS:
        invalid_type = ext.replace(".", "").upper() if ext else "UNKNOWN"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format '{invalid_type}'. Data ingestion strictly requires tabular spreadsheet files (.CSV, .XLS, .XLSX, .XLSB, .XLSM, .PARQUET, .JSON). Non-tabular formats such as .PDF, .TXT, .MD, .ZIP, .HTML are not supported."
        )

    # Save to disk with absolute path
    file_id = str(uuid.uuid4())
    safe_original_name = os.path.basename(file.filename or f"upload{ext}")
    save_filename = f"{file_id}_{safe_original_name}"
    file_path = str((_user_upload_dir(current_user) / save_filename).resolve())

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB upload limit")
    with open(file_path, "wb") as f:
        f.write(content)

    file_type = ext.replace(".", "").upper()

    try:
        preview = preview_import_file(file_path, file_type)
        preview["headers"] = preview.get("detected_headers", [])
        preview["preview_rows"] = preview.get("sample_rows", [])
        preview["total_rows_estimate"] = preview.get("total_detected_rows", 0)
        preview["file_path"] = file_path
        preview["file_name"] = file.filename
        preview["file_type"] = file_type
        return preview
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {str(exc)}"
        )


@router.post("/preview", response_model=ImportPreviewResponse)
async def preview_import(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    return await upload_import_file(file, current_user)


@router.post("/validate")
def validate_import_mapping(
    data: ValidateImportRequest,
    current_user: User = Depends(get_current_user)
):
    if not _can_manage_imports(current_user):
        raise HTTPException(status_code=403, detail="Import management privilege required")

    _resolve_user_upload(data.file_path, current_user)

    mapping = data.column_mapping or {}
    has_contact = any(k in mapping.values() for k in ("contact_name", "contact_phone", "contact_email", "company_name", "title"))
    return {
        "valid": has_contact,
        "mapped_fields_count": len(mapping),
        "message": "Mapping valid for lead ingestion" if has_contact else "Please map at least title, company, or contact information."
    }


@router.post("/execute", response_model=ImportJobOut, status_code=status.HTTP_202_ACCEPTED)
def execute_import(
    data: ImportJobExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: Optional[str] = Depends(get_optional_tenant_id)
):
    # RBAC: Telecallers must never execute imports
    if not _can_manage_imports(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telecallers do not have permission to execute dataset imports."
        )

    import json as py_json
    file_path = _resolve_user_upload(data.file_path, current_user)

    target_org_id = None
    schema_name = None

    job_type = (data.job_type or "TENANT_LEADS").upper()
    if job_type in ("GLOBAL_COMPANIES", "GLOBAL_DATABASE", "GLOBAL_PEOPLE"):
        if not (current_user.is_super_admin or current_user.platform_role in ("DATA_ENTRY", "DATA_OPS") or current_user.tenant_role == "DATA_ENTRY"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin or Data Entry privilege required for Global Database ingestion")
        target_org_id = None
        # Explicitly ensure clean public schema for global jobs
        if db.bind and db.bind.dialect.name == "postgresql":
            db.execute(text('SET search_path TO public'))
    else:
        if not tenant_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant context required for tenant lead import")
        target_org_id = tenant_id
        if current_user.tenant_role not in ("ORG_ADMIN", "SALES_MANAGER"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Organization Admins or Sales Managers can import tenant leads")
        # Resolve schema_name
        if target_org_id and db.bind and db.bind.dialect.name == "postgresql":
            from app.models.organization import Organization
            org = db.query(Organization).filter(Organization.id == target_org_id).first()
            if org and org.schema_name:
                schema_name = org.schema_name
                db.execute(text(f'SET search_path TO "{schema_name}", public'))

    now = utc_now()
    job_id = str(uuid.uuid4())
    col_map = data.column_mapping or {}

    if target_org_id and data.target_owner_id:
        owner = db.query(User).filter(
            User.id == data.target_owner_id,
            User.organization_id == target_org_id,
            User.tenant_role == "TELECALLER",
            User.status == "ACTIVE",
            User.deleted_at.is_(None),
        ).first()
        if not owner:
            raise HTTPException(status_code=400, detail="Target owner must be an active telecaller in this organization")
    if target_org_id and data.default_product_service_id:
        from app.models.product_service import ProductService
        product = db.query(ProductService.id).filter(
            ProductService.id == data.default_product_service_id,
            ProductService.organization_id == target_org_id,
            ProductService.is_active.is_(True),
        ).first()
        if not product:
            raise HTTPException(status_code=400, detail="Default Product/Service is not active in this organization")

    # Create ImportJob record
    job = ImportJob(
        id=job_id,
        organization_id=target_org_id,
        uploaded_by=current_user.id,
        job_type=job_type,
        file_name=data.file_name,
        file_type=data.file_type,
        file_path=file_path,
        column_mapping=col_map,
        target_stage_id=data.target_stage_id,
        target_owner_id=data.target_owner_id,
        default_product_service_id=data.default_product_service_id,
        status="PENDING",
        total_rows=0,
        processed_rows=0,
        successful_rows=0,
        duplicate_rows=0,
        error_rows=0,
        created_at=now
    )
    db.add(job)
    db.commit()

    # Dual-sync to public.import_jobs if created in a tenant schema, so queries with search_path=public can immediately see it
    if schema_name and db.bind and db.bind.dialect.name == "postgresql":
        try:
            db.execute(text("""
                INSERT INTO public.import_jobs 
                (id, organization_id, uploaded_by, job_type, file_name, file_type, file_path, column_mapping, target_stage_id, target_owner_id, default_product_service_id, status, total_rows, processed_rows, successful_rows, duplicate_rows, error_rows, created_at, error_summary)
                VALUES (:id, :org_id, :user_id, :job_type, :file_name, :file_type, :file_path, :column_mapping, :target_stage_id, :target_owner_id, :default_product_service_id, :status, :total_rows, :processed_rows, :successful_rows, :duplicate_rows, :error_rows, :created_at, :error_summary)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": job_id,
                "org_id": target_org_id,
                "user_id": current_user.id,
                "job_type": job_type,
                "file_name": data.file_name,
                "file_type": data.file_type,
                "file_path": file_path,
                "column_mapping": py_json.dumps(col_map),
                "target_stage_id": data.target_stage_id,
                "target_owner_id": data.target_owner_id,
                "default_product_service_id": data.default_product_service_id,
                "status": "PENDING",
                "total_rows": 0,
                "processed_rows": 0,
                "successful_rows": 0,
                "duplicate_rows": 0,
                "error_rows": 0,
                "created_at": now,
                "error_summary": "{}"
            })
            db.commit()
        except Exception as sync_exc:
            logger.debug(f"public.import_jobs dual-sync notice: {sync_exc}")

    # Expunge job to prevent any expired attribute reload crash
    try:
        db.expunge(job)
    except Exception:
        pass

    # Enqueue execution asynchronously in Celery
    run_import_job.delay(job_id)

    # Audit row on every import (Problem 1)
    try:
        from app.models.audit import RadarEvent
        db.add(RadarEvent(
            organization_id=target_org_id,
            actor_user_id=current_user.id,
            action="IMPORT_EXECUTED",
            entity_type="IMPORT_JOB",
            entity_id=job_id,
            payload_json={
                "file_name": data.file_name,
                "job_type": job_type,
                "uploaded_by": current_user.id
            }
        ))
        db.commit()
    except Exception as audit_err:
        logger.debug(f"Audit log error on import execute: {audit_err}")

    return ImportJobOut(
        id=job_id,
        organization_id=target_org_id,
        uploaded_by=current_user.id,
        uploader_name=current_user.full_name,
        job_type=job_type,
        file_name=data.file_name,
        file_type=data.file_type,
        total_rows=0,
        processed_rows=0,
        successful_rows=0,
        duplicate_rows=0,
        error_rows=0,
        status="PENDING",
        column_mapping=col_map,
        error_summary={},
        started_at=None,
        completed_at=None,
        created_at=now
    )


@router.get("/jobs", response_model=List[ImportJobOut])
def list_import_jobs(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: Optional[str] = Depends(get_optional_tenant_id)
):
    query = db.query(ImportJob)
    if not (current_user.is_super_admin and not tenant_id):
        query = query.filter(ImportJob.organization_id == tenant_id)
    jobs = query.order_by(ImportJob.created_at.desc()).offset(skip).limit(limit).all()

    # If no jobs found in active search path and PostgreSQL, check public schema as well
    if len(jobs) == 0 and db.bind and db.bind.dialect.name == "postgresql":
        try:
            db.execute(text('SET search_path TO public'))
            query2 = db.query(ImportJob)
            if not (current_user.is_super_admin and not tenant_id):
                query2 = query2.filter(ImportJob.organization_id == tenant_id)
            jobs = query2.order_by(ImportJob.created_at.desc()).offset(skip).limit(limit).all()
        except Exception:
            pass

    return [
        ImportJobOut(
            id=j.id,
            organization_id=j.organization_id,
            uploaded_by=j.uploaded_by,
            uploader_name=j.uploader.full_name if j.uploader else None,
            job_type=j.job_type,
            file_name=j.file_name,
            file_type=j.file_type,
            total_rows=j.total_rows,
            processed_rows=j.processed_rows,
            successful_rows=j.successful_rows,
            duplicate_rows=j.duplicate_rows,
            error_rows=j.error_rows,
            status=j.status,
            column_mapping=j.column_mapping,
            error_summary=j.error_summary or {},
            started_at=j.started_at,
            completed_at=j.completed_at,
            created_at=j.created_at
        )
        for j in jobs
    ]


@router.get("/jobs/{id}", response_model=ImportJobOut)
def get_import_job(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: Optional[str] = Depends(get_optional_tenant_id)
):
    query = db.query(ImportJob).filter(ImportJob.id == id)
    if not current_user.is_super_admin:
        query = query.filter(ImportJob.organization_id == tenant_id)
    job = query.first()

    # Fallback search across public and tenant schemas if not found in current search path
    if not job and db.bind and db.bind.dialect.name == "postgresql":
        try:
            db.execute(text('SET search_path TO public'))
            query_pub = db.query(ImportJob).filter(ImportJob.id == id)
            if not current_user.is_super_admin:
                query_pub = query_pub.filter(ImportJob.organization_id == tenant_id)
            job = query_pub.first()

            if not job:
                schemas = db.execute(text("SELECT schema_name FROM organizations WHERE schema_name IS NOT NULL")).scalars().all()
                for s in schemas:
                    db.execute(text(f'SET search_path TO "{s}", public'))
                    job = db.query(ImportJob).filter(ImportJob.id == id).first()
                    if job:
                        if not current_user.is_super_admin and job.organization_id != tenant_id:
                            job = None
                        break
        except Exception as fallback_exc:
            logger.debug(f"get_import_job schema fallback error: {fallback_exc}")

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")

    return ImportJobOut(
        id=job.id,
        organization_id=job.organization_id,
        uploaded_by=job.uploaded_by,
        uploader_name=job.uploader.full_name if job.uploader else None,
        job_type=job.job_type,
        file_name=job.file_name,
        file_type=job.file_type,
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        successful_rows=job.successful_rows,
        duplicate_rows=job.duplicate_rows,
        error_rows=job.error_rows,
        status=job.status,
        column_mapping=job.column_mapping,
        error_summary=job.error_summary or {},
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at
    )


@router.get("/jobs/{id}/errors", response_model=List[ImportRowErrorOut])
def get_import_row_errors(
    id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    job = db.query(ImportJob).filter(
        ImportJob.id == id,
        ImportJob.organization_id == tenant_id
    ).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")

    errors = db.query(ImportRowError).filter(
        ImportRowError.job_id == id
    ).order_by(ImportRowError.row_number.asc()).offset(skip).limit(limit).all()

    return errors


@router.get("/{id}/status")
def get_import_status(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: Optional[str] = Depends(get_optional_tenant_id)
):
    job = get_import_job(id, db, current_user, tenant_id)
    return {
        "id": job.id,
        "status": job.status,
        "total_rows": job.total_rows,
        "processed_rows": job.processed_rows,
        "successful_rows": job.successful_rows,
        "error_rows": job.error_rows,
        "duplicate_rows": job.duplicate_rows,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }


@router.get("/{id}/errors", response_model=List[ImportRowErrorOut])
def get_import_errors_alias(
    id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    return get_import_row_errors(id, skip, limit, db, current_user, tenant_id)


@router.post("/{id}/assign")
def assign_import_batch(
    id: str,
    data: AssignImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Distributes leads created by an import batch directly to telecallers using an assignment strategy:
    Round Robin or Capacity-Based.
    """
    if not (current_user.is_org_admin or current_user.tenant_role in ("ORG_ADMIN", "SALES_MANAGER", "SUPER_ADMIN")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ORG Admins and Sales Managers can assign import batches"
        )

    # Find target telecallers
    if data.telecaller_ids:
        telecallers = db.query(User).filter(
            User.organization_id == tenant_id,
            User.id.in_(data.telecaller_ids),
            User.status == "ACTIVE",
            User.deleted_at.is_(None),
            User.tenant_role == "TELECALLER"
        ).all()
    else:
        telecallers = db.query(User).filter(
            User.organization_id == tenant_id,
            User.tenant_role == "TELECALLER",
            User.status == "ACTIVE",
            User.deleted_at.is_(None)
        ).all()

    if not telecallers:
        raise HTTPException(status_code=400, detail="No active telecallers found in organization for assignment")

    # Find unassigned leads or leads assigned to uploader
    from sqlalchemy import or_
    leads = db.query(Lead).filter(
        Lead.organization_id == tenant_id,
        or_(
            Lead.owner_id == None,
            Lead.owner_id == current_user.id
        ),
        Lead.status != "ARCHIVED"
    ).limit(500).all()

    if not leads:
        return {"assigned_count": 0, "message": "No unassigned leads found to distribute"}

    # Round-robin distribution
    assigned_count = 0
    num_callers = len(telecallers)
    for idx, lead in enumerate(leads):
        target_caller = telecallers[idx % num_callers]
        lead.owner_id = target_caller.id
        assigned_count += 1

    db.commit()
    return {
        "assigned_count": assigned_count,
        "strategy": data.strategy,
        "telecallers_count": num_callers,
        "message": f"Successfully distributed {assigned_count} leads across {num_callers} telecallers using {data.strategy}."
    }
