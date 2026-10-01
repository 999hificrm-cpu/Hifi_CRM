import pytest
from app.services.lead_service import create_lead
from app.schemas.lead import LeadCreate


def test_login_success(client, tenant_a_fixture):
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin@alpha.com",
        "password": "Password@123"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "admin@alpha.com"
    assert data["user"]["tenant_role"] == "ORG_ADMIN"


def test_login_invalid_password(client):
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin@alpha.com",
        "password": "WrongPassword"
    })
    assert resp.status_code == 401


def test_telecaller_data_masking(client, db_session, tenant_a_fixture):
    # Create a lead with sensitive contact details
    lead = create_lead(
        db=db_session,
        organization_id=tenant_a_fixture["org"].id,
        data=LeadCreate(
            title="Masking Test Lead",
            company_name="Confidential Corp",
            contact_name="Vipin Kumar",
            contact_phone="+91 98765 43210",
            contact_email="vipin.kumar@confidential.com"
        ),
        creator_user=tenant_a_fixture["admin_user"]
    )
    # Telecallers may inspect only leads explicitly assigned to them.  This
    # test verifies masking within that authorized scope, not an old global
    # telecaller-access behavior.
    lead.owner_id = tenant_a_fixture["telecaller_user"].id
    db_session.commit()

    # 1. Tenant Admin sees UNMASKED data
    admin_headers = {"Authorization": f"Bearer {tenant_a_fixture['admin_token']}"}
    admin_resp = client.get(f"/api/v1/leads/{lead.id}", headers=admin_headers)
    assert admin_resp.status_code == 200
    admin_data = admin_resp.json()
    assert admin_data["contact_phone"] in ("+91 98765 43210", "+919876543210")
    assert admin_data["contact_email"] == "vipin.kumar@confidential.com"
    assert admin_data["is_phone_masked"] is False

    # 2. Telecaller sees MASKED data (anti-theft protection)
    tc_headers = {"Authorization": f"Bearer {tenant_a_fixture['telecaller_token']}"}
    tc_resp = client.get(f"/api/v1/leads/{lead.id}", headers=tc_headers)
    assert tc_resp.status_code == 200
    tc_data = tc_resp.json()
    assert "****" in tc_data["contact_phone"]
    assert "****" in tc_data["contact_email"]
    assert tc_data["is_phone_masked"] is True
    assert tc_data["is_email_masked"] is True
