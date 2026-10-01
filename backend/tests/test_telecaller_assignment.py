from datetime import datetime, timezone

from app.core.business_time import organization_business_date
from app.models.session import AttendanceSession
from app.schemas.lead import LeadCreate
from app.services.lead_service import create_lead


def test_telecaller_scoping_and_batch_assignment(client, db_session, tenant_a_fixture):
    tenant = tenant_a_fixture
    stage_id = tenant["org"].pipelines[0].stages[0].id
    leads = [
        create_lead(
            db_session,
            tenant["org"].id,
            LeadCreate(title=f"Assignment regression {index}", pipeline_stage_id=stage_id),
            tenant["admin_user"],
        )
        for index in range(5)
    ]

    existing_shift = db_session.query(AttendanceSession).filter(
        AttendanceSession.organization_id == tenant["org"].id,
        AttendanceSession.user_id == tenant["telecaller_user"].id,
        AttendanceSession.logout_at.is_(None),
    ).first()
    if not existing_shift:
        db_session.add(
            AttendanceSession(
                organization_id=tenant["org"].id,
                user_id=tenant["telecaller_user"].id,
                date=organization_business_date(db_session, tenant["org"].id),
                login_at=datetime.now(timezone.utc),
            )
        )
        db_session.commit()

    response = client.post(
        "/api/v1/leads/batch-assign",
        json={
            "lead_ids": [lead.id for lead in leads],
            "telecaller_id": tenant["telecaller_user"].id,
        },
        headers={"Authorization": f"Bearer {tenant['admin_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["updated_count"] == 5
    assert response.json()["skipped_count"] == 0

    visible = client.get(
        "/api/v1/leads/",
        headers={"Authorization": f"Bearer {tenant['telecaller_token']}"},
    )
    assert visible.status_code == 200
    visible_by_id = {lead["id"]: lead for lead in visible.json()}
    for lead in leads:
        assert visible_by_id[lead.id]["owner_id"] == tenant["telecaller_user"].id
