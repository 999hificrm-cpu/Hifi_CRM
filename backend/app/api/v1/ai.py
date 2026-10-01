from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user, get_tenant_id
from app.models.user import User
from app.schemas.ai import AIScoreResponse, AISummaryResponse, NextBestActionResponse
from app.services.ai_service import score_lead_ai, summarize_lead_ai, recommend_next_action_ai

router = APIRouter(prefix="/ai", tags=["AI Copilot & Intelligence Layer"])


@router.post("/leads/{id}/score", response_model=AIScoreResponse)
def compute_lead_score(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    return score_lead_ai(db, id, tenant_id, current_user.id)


@router.get("/leads/{id}/summary", response_model=AISummaryResponse)
def get_lead_ai_summary(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    return summarize_lead_ai(db, id, tenant_id, current_user.id)


@router.get("/leads/{id}/recommendation", response_model=NextBestActionResponse)
def get_next_best_action(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    return recommend_next_action_ai(db, id, tenant_id)
