import pytest
from app.services.lead_service import create_lead
from app.schemas.lead import LeadCreate


def test_cross_tenant_isolation(client, db_session, tenant_a_fixture, tenant_b_fixture):
    # 1. Tenant Alpha creates lead
    lead_alpha = create_lead(
        db=db_session,
        organization_id=tenant_a_fixture["org"].id,
        data=LeadCreate(
            title="Alpha Exclusive Deal",
            company_name="Alpha Tech",
            contact_name="Alpha Contact",
            contact_phone="+91 99999 11111"
        ),
        creator_user=tenant_a_fixture["admin_user"]
    )

    # 2. Tenant Alpha can access their own lead
    alpha_headers = {"Authorization": f"Bearer {tenant_a_fixture['admin_token']}"}
    resp = client.get(f"/api/v1/leads/{lead_alpha.id}", headers=alpha_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Alpha Exclusive Deal"

    # 3. Tenant Beta CANNOT access Alpha's lead (Must return 404 Not Found)
    beta_headers = {"Authorization": f"Bearer {tenant_b_fixture['admin_token']}"}
    resp_beta = client.get(f"/api/v1/leads/{lead_alpha.id}", headers=beta_headers)
    assert resp_beta.status_code == 404

    # 4. Tenant Beta cannot mutate Alpha's lead stage
    beta_stage_id = tenant_b_fixture["org"].pipelines[0].stages[1].id
    mutate_resp = client.post(
        f"/api/v1/leads/{lead_alpha.id}/stage",
        headers=beta_headers,
        json={"stage_id": beta_stage_id, "reason": "Malicious cross-tenant jump"}
    )
    assert mutate_resp.status_code == 404

    # 5. Lead listing shows only tenant's own data
    list_beta = client.get("/api/v1/leads/", headers=beta_headers)
    assert list_beta.status_code == 200
    beta_lead_ids = [l["id"] for l in list_beta.json()]
    assert lead_alpha.id not in beta_lead_ids
