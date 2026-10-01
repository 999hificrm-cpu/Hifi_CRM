"""Regression tests for Telecaller Lead filters and contact-card downloads."""
from app.core.security import create_access_token, get_password_hash
from app.models.lead import Lead
from app.models.user import User
from app.schemas.lead import LeadCreate
from app.services.lead_service import create_lead


def _create_assigned_lead(db_session, tenant, title, segment):
    stage = tenant["org"].pipelines[0].stages[0]
    lead = create_lead(
        db_session,
        tenant["org"].id,
        LeadCreate(
            title=title,
            contact_name=f"{title} Contact",
            company_name="Acme",
            contact_phone="9876543210",
            contact_email="contact@acme.example",
            pipeline_stage_id=stage.id,
            segment=segment,
        ),
        tenant["admin_user"],
    )
    lead.owner_id = tenant["telecaller_user"].id
    db_session.commit()
    return lead


def test_telecaller_segment_filters_are_backend_authoritative(client, db_session, tenant_a_fixture):
    tenant = tenant_a_fixture
    b2b = _create_assigned_lead(db_session, tenant, "Business lead", "B2B")
    b2c = _create_assigned_lead(db_session, tenant, "Consumer lead", "B2C")
    other = _create_assigned_lead(db_session, tenant, "Unqualified lead", "OTHER")
    legacy = _create_assigned_lead(db_session, tenant, "Legacy lead", "B2B")
    legacy.segment = None
    db_session.commit()

    headers = {"Authorization": f"Bearer {tenant['telecaller_token']}"}
    for filter_name, expected_ids in {
        "B2B": {b2b.id},
        "B2C": {b2c.id},
        "OTHER": {other.id, legacy.id},
    }.items():
        response = client.get(f"/api/v1/leads/?segment={filter_name}", headers=headers)
        assert response.status_code == 200
        returned = response.json()
        returned_ids = {lead["id"] for lead in returned}
        assert expected_ids <= returned_ids
        if filter_name in {"B2B", "B2C"}:
            assert {lead["segment"] for lead in returned} == {filter_name}
        else:
            assert all(lead.get("segment") in {None, "OTHER"} for lead in returned)

    invalid = client.get("/api/v1/leads/?segment=ENTERPRISE", headers=headers)
    assert invalid.status_code == 422


def test_vcard_requires_assigned_lead_access_and_respects_masking(client, db_session, tenant_a_fixture):
    tenant = tenant_a_fixture
    lead = _create_assigned_lead(db_session, tenant, "Card lead", "B2B")
    headers = {"Authorization": f"Bearer {tenant['telecaller_token']}"}

    response = client.get(f"/api/v1/leads/{lead.id}/vcard", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/vcard")
    assert "BEGIN:VCARD" in response.text
    # The default telecaller policy masks phone and email, so exporting a card
    # cannot become an unmasking backdoor.
    assert "9876543210" not in response.text
    assert "contact@acme.example" not in response.text

    other = User(
        organization_id=tenant["org"].id,
        tenant_role="TELECALLER",
        full_name="Other Caller",
        email="vcard.other@alpha.com",
        password_hash=get_password_hash("Password@123"),
        status="ACTIVE",
    )
    db_session.add(other)
    db_session.commit()
    other_headers = {"Authorization": f"Bearer {create_access_token(other.id)}"}
    denied = client.get(f"/api/v1/leads/{lead.id}/vcard", headers=other_headers)
    assert denied.status_code == 404
