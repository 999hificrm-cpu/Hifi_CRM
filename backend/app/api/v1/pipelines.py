from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user, require_org_admin, get_tenant_id
from app.models.user import User
from app.models.pipeline import Pipeline, PipelineStage
from app.schemas.pipeline import PipelineOut, PipelineStageOut, PipelineStageCreate, PipelineStageUpdate
from app.services.pipeline_service import get_default_pipeline, list_stages, get_stage_by_id

router = APIRouter(prefix="/pipelines", tags=["Pipelines & Stages"])


@router.get("/", response_model=PipelineOut)
def get_organization_pipeline(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    pipeline = get_default_pipeline(db, tenant_id)
    stages = list_stages(db, tenant_id, pipeline.id)
    return PipelineOut(
        id=pipeline.id,
        organization_id=pipeline.organization_id,
        name=pipeline.name,
        description=pipeline.description,
        is_default=pipeline.is_default,
        status=pipeline.status,
        stages=[PipelineStageOut.model_validate(s) for s in stages],
        created_at=pipeline.created_at
    )


@router.post("/stages", response_model=PipelineStageOut, status_code=status.HTTP_201_CREATED)
def add_pipeline_stage(
    data: PipelineStageCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_org_admin),
    tenant_id: str = Depends(get_tenant_id)
):
    pipeline = get_default_pipeline(db, tenant_id)

    stage = PipelineStage(
        pipeline_id=pipeline.id,
        name=data.name.strip(),
        code=data.code.strip().upper(),
        order_index=data.order_index,
        color=data.color or "#3b82f6",
        win_probability=data.win_probability,
        is_won=data.is_won,
        is_lost=data.is_lost
    )
    db.add(stage)
    db.commit()
    try:
        db.refresh(stage)
    except Exception:
        pass
    return stage


@router.put("/stages/{id}", response_model=PipelineStageOut)
def update_pipeline_stage(
    id: str,
    data: PipelineStageUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_org_admin),
    tenant_id: str = Depends(get_tenant_id)
):
    stage = get_stage_by_id(db, id, tenant_id)
    if data.name:
        stage.name = data.name.strip()
    if data.code:
        stage.code = data.code.strip().upper()
    if data.order_index is not None:
        stage.order_index = data.order_index
    if data.color:
        stage.color = data.color
    if data.win_probability is not None:
        stage.win_probability = data.win_probability
    if data.is_won is not None:
        stage.is_won = data.is_won
    if data.is_lost is not None:
        stage.is_lost = data.is_lost

    db.commit()
    try:
        db.refresh(stage)
    except Exception:
        pass
    return stage
