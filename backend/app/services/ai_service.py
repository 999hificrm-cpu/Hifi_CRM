from typing import Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.models.lead import Lead
from app.models.ai import AIRun, AIInsight
from app.models.activity import Activity
from app.models.task import Task
from app.schemas.ai import AIScoreResponse, AISummaryResponse, NextBestActionResponse


def score_lead_ai(db: Session, lead_id: str, organization_id: str, user_id: str = None) -> AIScoreResponse:
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization_id
    ).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    signals = []
    base_score = 40

    # Signal 1: Corporate & Contact Completeness
    if lead.company_name:
        base_score += 15
        signals.append("Verified enterprise entity on record")
    if lead.contact_name:
        base_score += 10
        signals.append("Identified decision maker / executive contact")
    if lead.contact_phone:
        base_score += 15
        signals.append("Direct direct-dial phone available")
    if lead.contact_email:
        base_score += 10
        signals.append("Corporate email verified")

    # Signal 2: Recent Activity
    act_count = db.query(Activity).filter(Activity.lead_id == lead.id).count()
    if act_count >= 3:
        base_score += 15
        signals.append(f"High historical engagement ({act_count} interactions logged)")
    elif act_count > 0:
        base_score += 5
        signals.append("Initial interaction in progress")

    final_score = min(98, max(20, base_score))
    lead.score = final_score

    # Tier
    if final_score >= 85:
        tier = "HOT"
        prob = 0.82
    elif final_score >= 70:
        tier = "HIGH"
        prob = 0.65
    elif final_score >= 50:
        tier = "MEDIUM"
        prob = 0.40
    else:
        tier = "LOW"
        prob = 0.18

    # Record AI Run
    ai_run = AIRun(
        organization_id=organization_id,
        user_id=user_id,
        run_type="LEAD_SCORE",
        entity_type="LEAD",
        entity_id=lead.id,
        model="jarvis-intelligence-v1",
        input_data={"title": lead.title, "contact": lead.contact_name, "company": lead.company_name},
        output_data={"score": final_score, "tier": tier, "signals": signals},
        status="COMPLETED"
    )
    db.add(ai_run)
    db.commit()

    return AIScoreResponse(
        lead_id=lead.id,
        score=final_score,
        qualification_tier=tier,
        key_signals=signals,
        conversion_probability=prob
    )


def summarize_lead_ai(db: Session, lead_id: str, organization_id: str, user_id: str = None) -> AISummaryResponse:
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization_id
    ).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    activities = db.query(Activity).filter(Activity.lead_id == lead.id).order_by(Activity.occurred_at.desc()).limit(5).all()
    act_texts = [f"{a.activity_type}: {a.subject or a.description or 'Completed'}" for a in activities]
    act_summary = "; ".join(act_texts) if act_texts else "No prior recorded interactions."

    headline = f"High-potential opportunity with {lead.company_name or lead.title}"
    context = (
        f"This opportunity was sourced via {lead.source}. Currently in stage '{lead.stage.name if lead.stage else 'New'}' "
        f"with an estimated pipeline value of {lead.currency} {lead.value:,.2f}."
    )

    stakeholders = [lead.contact_name] if lead.contact_name else ["Executive Buyer (Pending identification)"]
    risks = []
    if not lead.contact_phone:
        risks.append("No phone number on file for rapid dialing")
    if not activities:
        risks.append("Lead has not been engaged yet")

    next_step = "Initiate exploratory call with decision maker to assess budget and timeline."

    return AISummaryResponse(
        lead_id=lead.id,
        headline=headline,
        business_context=context,
        key_stakeholders=stakeholders,
        past_interactions_summary=act_summary,
        risk_factors=risks or ["No critical risks identified"],
        suggested_next_step=next_step
    )


def recommend_next_action_ai(db: Session, lead_id: str, organization_id: str) -> NextBestActionResponse:
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization_id
    ).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    recent_act = db.query(Activity).filter(Activity.lead_id == lead.id).order_by(Activity.occurred_at.desc()).first()

    if not recent_act:
        return NextBestActionResponse(
            lead_id=lead.id,
            recommended_action="First Outreach Call",
            channel="CALL",
            reason="Fresh prospect: outbound call within 24h yields highest connect rates.",
            suggested_message=f"Hello {lead.contact_name or 'there'}, reaching out regarding your interest in our business solutions."
        )
    elif recent_act.activity_type == "CALL" and recent_act.status in ("NO_ANSWER", "BUSY"):
        return NextBestActionResponse(
            lead_id=lead.id,
            recommended_action="Follow-up WhatsApp Message",
            channel="WHATSAPP",
            reason="Previous call was unanswered; brief WhatsApp ping has 80%+ read rate.",
            suggested_message=f"Hi {lead.contact_name or ''}, tried reaching you briefly today. Let me know what time works best for a quick 5-min sync!"
        )
    else:
        return NextBestActionResponse(
            lead_id=lead.id,
            recommended_action="Share Executive Proposal / Deck",
            channel="EMAIL",
            reason="Lead is qualified and engaged; send formal proposal to advance pipeline.",
            suggested_message=f"Hi {lead.contact_name or ''}, following our discussion, attached is our proposal tailored for {lead.company_name or 'your team'}."
        )
