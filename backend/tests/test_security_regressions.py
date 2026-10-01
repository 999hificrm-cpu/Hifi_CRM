"""Regression coverage for critical object authorization and privilege boundaries."""
from app.core.security import create_access_token, get_password_hash
from app.models.lead import Lead
from app.models.product_service import ProductService
from app.models.user import User
from app.services.lead_service import create_lead
from app.schemas.lead import LeadCreate


def _other_telecaller(db_session, organization_id):
    user = User(
        organization_id=organization_id,
        tenant_role="TELECALLER",
        full_name="Unassigned Telecaller",
        email="unassigned.telecaller@alpha.com",
        password_hash=get_password_hash("Password@123"),
        status="ACTIVE",
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_telecaller_cannot_read_or_update_another_telecallers_lead(client, db_session, tenant_a_fixture):
    tenant = tenant_a_fixture
    other_telecaller = _other_telecaller(db_session, tenant["org"].id)
    stage = tenant["org"].pipelines[0].stages[0]
    lead = create_lead(
        db_session,
        tenant["org"].id,
        LeadCreate(title="Restricted lead", company_name="Acme", pipeline_stage_id=stage.id),
        tenant["admin_user"],
    )
    lead.owner_id = other_telecaller.id
    db_session.commit()

    headers = {"Authorization": f"Bearer {tenant['telecaller_token']}"}
    assert client.get(f"/api/v1/leads/{lead.id}", headers=headers).status_code == 404
    assert client.get(f"/api/v1/leads/{lead.id}/timeline", headers=headers).status_code == 404
    assert client.patch(f"/api/v1/leads/{lead.id}", headers=headers, json={"notes": "tampered"}).status_code == 404


def test_lead_status_cannot_bypass_stage_lifecycle(client, db_session, tenant_a_fixture):
    tenant = tenant_a_fixture
    stage = tenant["org"].pipelines[0].stages[0]
    lead = create_lead(
        db_session,
        tenant["org"].id,
        LeadCreate(title="Lifecycle lead", company_name="Acme", pipeline_stage_id=stage.id),
        tenant["admin_user"],
    )
    headers = {"Authorization": f"Bearer {tenant['admin_token']}"}
    response = client.patch(f"/api/v1/leads/{lead.id}", headers=headers, json={"status": "WON"})
    assert response.status_code == 422
    assert db_session.get(Lead, lead.id).status == "OPEN"


def test_cross_tenant_product_service_is_rejected_on_update(client, db_session, tenant_a_fixture, tenant_b_fixture):
    stage = tenant_a_fixture["org"].pipelines[0].stages[0]
    lead = create_lead(
        db_session,
        tenant_a_fixture["org"].id,
        LeadCreate(title="Product boundary", company_name="Acme", pipeline_stage_id=stage.id),
        tenant_a_fixture["admin_user"],
    )
    foreign_product = ProductService(organization_id=tenant_b_fixture["org"].id, name="Tenant B product", type="PRODUCT")
    db_session.add(foreign_product)
    db_session.commit()
    headers = {"Authorization": f"Bearer {tenant_a_fixture['admin_token']}"}
    response = client.patch(f"/api/v1/leads/{lead.id}", headers=headers, json={"product_service_id": foreign_product.id})
    assert response.status_code == 400


def test_org_admin_cannot_grant_platform_permission(client, tenant_a_fixture):
    headers = {"Authorization": f"Bearer {tenant_a_fixture['admin_token']}"}
    response = client.patch(
        f"/api/v1/users/{tenant_a_fixture['telecaller_user'].id}",
        headers=headers,
        json={"permission_overrides": {"PLATFORM_EXPORT": True}},
    )
    assert response.status_code == 403
