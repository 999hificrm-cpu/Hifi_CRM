from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.pipeline import Pipeline, PipelineStage
from app.schemas.pipeline import PipelineStageCreate, PipelineStageUpdate


def get_default_pipeline(db: Session, organization_id: str) -> Pipeline:
    pipeline = db.query(Pipeline).filter(
        Pipeline.organization_id == organization_id,
        Pipeline.is_default == True,
        Pipeline.status == "ACTIVE"
    ).first()
    if not pipeline:
        pipeline = db.query(Pipeline).filter(
            Pipeline.organization_id == organization_id,
            Pipeline.status == "ACTIVE"
        ).first()
    if not pipeline:
        # Create default pipeline if missing
        pipeline = Pipeline(
            organization_id=organization_id,
            name="Standard Sales Pipeline",
            is_default=True,
            status="ACTIVE"
        )
        db.add(pipeline)
        db.flush()

        from app.services.organization_service import DEFAULT_PIPELINE_STAGES
        for s in DEFAULT_PIPELINE_STAGES:
            stage = PipelineStage(
                pipeline_id=pipeline.id,
                name=s["name"],
                code=s["code"],
                order_index=s["order_index"],
                color=s["color"],
                win_probability=s["win_probability"],
                is_won=s["is_won"],
                is_lost=s["is_lost"]
            )
            db.add(stage)
        db.commit()
        try:
            db.refresh(pipeline)
        except Exception:
            pass
    return pipeline


def get_first_stage(db: Session, organization_id: str) -> PipelineStage:
    pipeline = get_default_pipeline(db, organization_id)
    first_stage = db.query(PipelineStage).filter(
        PipelineStage.pipeline_id == pipeline.id
    ).order_by(PipelineStage.order_index.asc()).first()
    if not first_stage:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pipeline has no defined stages"
        )
    return first_stage


def get_stage_by_id(db: Session, stage_id: str, organization_id: str) -> PipelineStage:
    stage = db.query(PipelineStage).join(Pipeline).filter(
        PipelineStage.id == stage_id,
        Pipeline.organization_id == organization_id
    ).first()
    if not stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline stage {stage_id} not found in this organization"
        )
    return stage


def list_stages(db: Session, organization_id: str, pipeline_id: Optional[str] = None) -> List[PipelineStage]:
    query = db.query(PipelineStage).join(Pipeline).filter(Pipeline.organization_id == organization_id)
    if pipeline_id:
        query = query.filter(PipelineStage.pipeline_id == pipeline_id)
    else:
        pipeline = get_default_pipeline(db, organization_id)
        query = query.filter(PipelineStage.pipeline_id == pipeline.id)
    return query.order_by(PipelineStage.order_index.asc()).all()
