from sqlalchemy import func, text

from app.models.lead import Lead
from app.models.organization import Organization
from app.models.pipeline import Pipeline, PipelineStage


def test_new_org_admin_isolated_schema_and_fresh_dashboard(
    client, db_session, superadmin_token
):
    """A newly provisioned tenant starts empty with the canonical pipeline.

    PostgreSQL-specific schema assertions run only when the suite is backed by
    PostgreSQL; tenant-boundary behavior is still exercised on SQLite.
    """
    admin_headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = client.post(
        "/api/v1/organizations/",
        json={
            "name": "Adani Industries LTD.",
            "slug": "adani-industries-ltd",
            "admin_name": "Gautam Adani",
            "admin_email": "admin@adani.com",
            "admin_password": "AdaniAdmin@2026",
            "plan_code": "GROWTH",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    org_id = response.json()["id"]

    db_session.expire_all()
    organization = db_session.query(Organization).filter(Organization.id == org_id).one()
    assert db_session.query(Lead).filter(Lead.organization_id == org_id).count() == 0
    public_stage_count = (
        db_session.query(func.count(PipelineStage.id))
        .join(Pipeline, Pipeline.id == PipelineStage.pipeline_id)
        .filter(Pipeline.organization_id == org_id)
        .scalar()
    )
    assert public_stage_count == 7

    if db_session.bind.dialect.name == "postgresql":
        schema_name = organization.schema_name
        assert db_session.execute(
            text(f'SELECT count(*) FROM "{schema_name}"."leads"')
        ).scalar() == 0
        assert db_session.execute(
            text(f'SELECT count(*) FROM "{schema_name}"."pipeline_stages"')
        ).scalar() == 7

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@adani.com", "password": "AdaniAdmin@2026"},
    )
    assert login.status_code == 200
    tenant_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    leads = client.get("/api/v1/leads/", headers=tenant_headers)
    assert leads.status_code == 200
    assert leads.json() == []

    pipeline = client.get("/api/v1/pipelines/", headers=tenant_headers)
    assert pipeline.status_code == 200
    assert len(pipeline.json()["stages"]) == 7

    global_companies = client.get("/api/v1/global/companies", headers=tenant_headers)
    assert global_companies.status_code == 200
    assert isinstance(global_companies.json(), list)
