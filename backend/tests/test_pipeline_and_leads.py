import pytest
from app.services.lead_service import create_lead
from app.schemas.lead import LeadCreate
from app.models.lead_history import LeadStageHistory


def test_stage_progression_and_history(client, db_session, tenant_a_fixture):
    headers = {"Authorization": f"Bearer {tenant_a_fixture['admin_token']}"}
    stages = tenant_a_fixture["org"].pipelines[0].stages
    stage_new = stages[0]
    stage_contacted = stages[1]
    stage_won = [s for s in stages if s.is_won][0]

    # Create lead
    lead = create_lead(
        db=db_session,
        organization_id=tenant_a_fixture["org"].id,
        data=LeadCreate(
            title="Solar Project Apex",
            company_name="Solar Tech",
            contact_name="Ramesh",
            pipeline_stage_id=stage_new.id
        ),
        creator_user=tenant_a_fixture["admin_user"]
    )

    # 1. Move to "Contacted"
    resp = client.post(
        f"/api/v1/leads/{lead.id}/stage",
        headers=headers,
        json={"stage_id": stage_contacted.id, "reason": "Initial call connected"}
    )
    assert resp.status_code == 200
    assert resp.json()["pipeline_stage_id"] == stage_contacted.id
    assert resp.json()["status"] == "OPEN"

    # Verify stage history table
    hist_resp = client.get(f"/api/v1/leads/{lead.id}/stage-history", headers=headers)
    assert hist_resp.status_code == 200
    histories = hist_resp.json()
    assert len(histories) >= 2  # Creation + 1 transition
    assert histories[0]["to_stage_id"] == stage_contacted.id
    assert histories[0]["reason"] == "Initial call connected"

    # 2. Move to "Won"
    resp_won = client.post(
        f"/api/v1/leads/{lead.id}/stage",
        headers=headers,
        json={"stage_id": stage_won.id, "reason": "Deal closed and signed"}
    )
    assert resp_won.status_code == 200
    assert resp_won.json()["status"] == "WON"
