import pytest
from app.models.global_registry import GlobalCompany, GlobalContact, GlobalCompanyContactMap
from app.models.organization import Subscription
from app.services.global_service import pull_global_companies_to_crm
from app.services.lead_service import create_lead
from app.schemas.lead import LeadCreate
from app.services.ai_service import score_lead_ai, summarize_lead_ai, recommend_next_action_ai


def test_global_pull_with_quota(db_session, tenant_a_fixture):
    org = tenant_a_fixture["org"]
    admin = tenant_a_fixture["admin_user"]

    # 1. Create a global company with mapped contact
    gc = GlobalCompany(
        registry_id="U12345MH2020PTC999999",
        legal_name="Global Solar Systems Pvt Ltd",
        industry="Renewable Energy",
        city="Pune"
    )
    db_session.add(gc)
    db_session.flush()

    gcont = GlobalContact(
        registry_id="09876543",
        full_name="Vikramaditya Rao",
        designation="Director",
        phone="+91 98980 12345",
        email="vikram@globalsolar.in"
    )
    db_session.add(gcont)
    db_session.flush()

    cmap = GlobalCompanyContactMap(company_id=gc.id, contact_id=gcont.id, designation="Director")
    db_session.add(cmap)
    db_session.commit()

    # 2. Check initial quota
    sub = db_session.query(Subscription).filter(Subscription.organization_id == org.id).first()
    initial_used = sub.pull_quota_used

    # 3. Pull to CRM
    result = pull_global_companies_to_crm(
        db=db_session,
        organization_id=org.id,
        user=admin,
        global_company_ids=[gc.id]
    )
    assert result.pulled_companies == 1
    assert result.pulled_contacts == 1
    assert result.created_leads == 1

    # 4. Verify quota was deducted
    db_session.refresh(sub)
    assert sub.pull_quota_used == initial_used + 1


def test_ai_lead_scoring_and_summary(db_session, tenant_a_fixture):
    org = tenant_a_fixture["org"]
    admin = tenant_a_fixture["admin_user"]

    lead = create_lead(
        db=db_session,
        organization_id=org.id,
        data=LeadCreate(
            title="AI Test Opportunity",
            company_name="Vortex Wind Energy",
            contact_name="Sanjay Gupta",
            contact_phone="+91 98200 44332",
            contact_email="sanjay@vortexwind.com",
            value=850000.00
        ),
        creator_user=admin
    )

    # 1. AI Scoring
    score_resp = score_lead_ai(db_session, lead.id, org.id, admin.id)
    assert score_resp.score >= 70
    assert score_resp.qualification_tier in ("HOT", "HIGH")
    assert len(score_resp.key_signals) >= 3

    # 2. AI Executive Summary
    summary_resp = summarize_lead_ai(db_session, lead.id, org.id, admin.id)
    assert "Vortex Wind Energy" in summary_resp.headline
    assert summary_resp.suggested_next_step is not None

    # 3. Next Best Action
    rec_resp = recommend_next_action_ai(db_session, lead.id, org.id)
    assert rec_resp.channel in ("CALL", "WHATSAPP", "EMAIL")
    assert rec_resp.recommended_action is not None
