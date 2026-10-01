from datetime import datetime, timedelta, timezone

from app.core.business_time import organization_business_date, organization_timezone
from app.models.activity import Activity
from app.models.call_record import CallRecord
from app.models.global_people import GlobalPerson
from app.models.organization import Subscription
from app.models.session import AttendanceSession
from app.models.task import Task
from app.models.lead_history import LeadStageHistory
from app.models.followup_policy import FollowupPolicy
from app.models.base import generate_uuid
from app.models.user import User
from app.schemas.activity import ActivityCreate
from app.schemas.lead import LeadCreate
from app.core.security import get_password_hash
from app.services.activity_service import create_activity
from app.services.global_people_service import pull_global_people_to_crm
from app.services.lead_service import create_lead


def _assigned_lead(db, tenant, title):
    return create_lead(
        db,
        tenant["org"].id,
        LeadCreate(
            title=title,
            pipeline_stage_id=tenant["org"].pipelines[0].stages[0].id,
            owner_id=tenant["telecaller_user"].id,
        ),
        tenant["admin_user"],
    )


def test_followup_preset_persists_one_task_and_call_record(db_session, tenant_a_fixture):
    tenant = tenant_a_fixture
    lead = _assigned_lead(db_session, tenant, "Preset regression lead")

    create_activity(
        db_session,
        tenant["org"].id,
        tenant["telecaller_user"],
        ActivityCreate(
            lead_id=lead.id,
            activity_type="CALL",
            status="CALLBACK",
            followup_preset="tomorrow",
        ),
    )

    tasks = db_session.query(Task).filter(
        Task.organization_id == tenant["org"].id,
        Task.lead_id == lead.id,
        Task.task_type == "FOLLOW_UP",
        Task.status == "PENDING",
    ).all()
    assert len(tasks) == 1
    due = tasks[0].due_at.replace(tzinfo=timezone.utc) if tasks[0].due_at.tzinfo is None else tasks[0].due_at
    local_due = due.astimezone(organization_timezone(db_session, tenant["org"].id))
    assert local_due.date() == organization_business_date(db_session, tenant["org"].id) + timedelta(days=1)
    assert (local_due.hour, local_due.minute) == (9, 0)

    record = db_session.query(CallRecord).filter(CallRecord.lead_id == lead.id).one()
    assert record.disposition == "CALLBACK"

    create_activity(
        db_session,
        tenant["org"].id,
        tenant["telecaller_user"],
        ActivityCreate(lead_id=lead.id, activity_type="CALL", status="CONNECTED", followup_preset="3days"),
    )
    assert db_session.query(Task).filter(
        Task.lead_id == lead.id, Task.task_type == "FOLLOW_UP", Task.status == "PENDING"
    ).count() == 1

    create_activity(
        db_session,
        tenant["org"].id,
        tenant["telecaller_user"],
        ActivityCreate(lead_id=lead.id, activity_type="CALL", status="CONNECTED", followup_preset="none"),
    )
    assert db_session.query(Task).filter(
        Task.lead_id == lead.id, Task.task_type == "FOLLOW_UP", Task.status == "PENDING"
    ).count() == 0


def test_batch_assignment_skips_already_owned_lead(client, db_session, tenant_a_fixture):
    tenant = tenant_a_fixture
    unowned = create_lead(
        db_session,
        tenant["org"].id,
        LeadCreate(title="Unowned batch lead", pipeline_stage_id=tenant["org"].pipelines[0].stages[0].id),
        tenant["admin_user"],
    )
    owned = _assigned_lead(db_session, tenant, "Already owned batch lead")
    db_session.add(AttendanceSession(
        organization_id=tenant["org"].id,
        user_id=tenant["telecaller_user"].id,
        date=organization_business_date(db_session, tenant["org"].id),
        login_at=datetime.now(timezone.utc),
    ))
    db_session.commit()

    response = client.post(
        "/api/v1/leads/batch-assign",
        headers={"Authorization": f"Bearer {tenant['admin_token']}"},
        json={"lead_ids": [unowned.id, owned.id], "telecaller_id": tenant["telecaller_user"].id},
    )
    assert response.status_code == 200
    assert response.json()["updated_count"] == 1
    assert response.json()["skipped_count"] == 1
    db_session.refresh(owned)
    assert owned.owner_id == tenant["telecaller_user"].id


def test_global_people_pull_is_idempotent_and_charges_success_only(db_session, tenant_a_fixture):
    tenant = tenant_a_fixture
    person = GlobalPerson(full_name="Quota Person Regression", email="quota-regression@example.com")
    db_session.add(person)
    db_session.commit()
    subscription = db_session.query(Subscription).filter(
        Subscription.organization_id == tenant["org"].id
    ).one()
    initial_used = subscription.pull_quota_used

    result = pull_global_people_to_crm(
        db_session,
        tenant["org"].id,
        tenant["admin_user"],
        [person.id, person.id, "missing-global-person"],
    )
    assert result.pulled_people == 1
    assert result.created_contacts == 1
    db_session.refresh(subscription)
    assert subscription.pull_quota_used == initial_used + 1

    retry = pull_global_people_to_crm(
        db_session,
        tenant["org"].id,
        tenant["admin_user"],
        [person.id],
    )
    assert retry.pulled_people == 0
    db_session.refresh(subscription)
    assert subscription.pull_quota_used == initial_used + 1


def test_product_lifecycle_context_and_tenant_boundary(
    client, db_session, tenant_a_fixture, tenant_b_fixture
):
    tenant = tenant_a_fixture
    admin_headers = {"Authorization": f"Bearer {tenant['admin_token']}"}
    created = client.post(
        "/api/v1/product-services/",
        headers=admin_headers,
        json={
            "name": "Data Science Course",
            "code": "DS-COURSE",
            "type": "SERVICE",
            "description": "Instructor-led course",
            "price": 25000,
            "currency": "INR",
            "is_active": True,
        },
    )
    assert created.status_code == 201
    product = created.json()

    lead = create_lead(
        db_session,
        tenant["org"].id,
        LeadCreate(
            title="Amit Sharma",
            pipeline_stage_id=tenant["org"].pipelines[0].stages[0].id,
            owner_id=tenant["telecaller_user"].id,
            product_service_id=product["id"],
            purpose="Interested in our data science course.",
        ),
        tenant["admin_user"],
    )
    lead_response = client.get(
        f"/api/v1/leads/{lead.id}",
        headers={"Authorization": f"Bearer {tenant['telecaller_token']}"},
    )
    assert lead_response.status_code == 200
    assert lead_response.json()["product_service_name"] == "Data Science Course"
    assert lead_response.json()["purpose"] == "Interested in our data science course."

    deactivated = client.patch(
        f"/api/v1/product-services/{product['id']}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    foreign_read = client.get(
        f"/api/v1/product-services/{product['id']}",
        headers={"Authorization": f"Bearer {tenant_b_fixture['admin_token']}"},
    )
    assert foreign_read.status_code == 404
    forbidden_mutation = client.post(
        "/api/v1/product-services/",
        headers={"Authorization": f"Bearer {tenant['telecaller_token']}"},
        json={"name": "Unauthorized", "type": "PRODUCT"},
    )
    assert forbidden_mutation.status_code == 403


def test_targets_and_shift_state_are_server_authoritative(client, db_session, tenant_a_fixture):
    tenant = tenant_a_fixture
    configured = client.patch(
        f"/api/v1/users/{tenant['telecaller_user'].id}",
        headers={"Authorization": f"Bearer {tenant['admin_token']}"},
        json={"telecaller_targets": {"calls": 80, "connects": 30, "talk_time": 120}},
    )
    assert configured.status_code == 200

    telecaller_headers = {"Authorization": f"Bearer {tenant['telecaller_token']}"}
    target = client.get("/api/v1/telecaller/targets/today", headers=telecaller_headers)
    assert target.status_code == 200
    assert target.json()["target_calls"] == 80
    assert target.json()["target_connects"] == 30
    assert target.json()["target_talk_time_minutes"] == 120
    assert target.json()["target_date"] == str(
        organization_business_date(db_session, tenant["org"].id)
    )

    # Isolate this lifecycle from any shift created by an earlier regression.
    now = datetime.now(timezone.utc)
    db_session.query(AttendanceSession).filter(
        AttendanceSession.organization_id == tenant["org"].id,
        AttendanceSession.user_id == tenant["telecaller_user"].id,
        AttendanceSession.logout_at.is_(None),
    ).update({AttendanceSession.logout_at: now}, synchronize_session=False)
    db_session.commit()

    started = client.post("/api/v1/shift/start", headers=telecaller_headers)
    assert started.status_code == 200
    duplicate = client.post("/api/v1/shift/start", headers=telecaller_headers)
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "already_started"
    assert client.post("/api/v1/shift/break-start", headers=telecaller_headers).status_code == 200
    active = client.get("/api/v1/shift/status", headers=telecaller_headers).json()
    assert active["is_active"] is True
    assert active["is_on_break"] is True
    assert active["shift_started_at"] is not None
    assert client.post("/api/v1/shift/end", headers=telecaller_headers).status_code == 200
    ended = client.get("/api/v1/shift/status", headers=telecaller_headers).json()
    assert ended["is_active"] is False
    assert ended["is_on_break"] is False


def test_queue_classification_is_disjoint_and_backend_counted(client, db_session, tenant_a_fixture):
    tenant = tenant_a_fixture
    followup_lead = _assigned_lead(db_session, tenant, "Queue follow-up lead")
    fresh_lead = _assigned_lead(db_session, tenant, "Queue fresh lead")
    db_session.add(
        Task(
            organization_id=tenant["org"].id,
            lead_id=followup_lead.id,
            task_type="FOLLOW_UP",
            title="Due callback",
            status="PENDING",
            priority="HIGH",
            due_at=datetime.now(timezone.utc),
            assigned_to=tenant["telecaller_user"].id,
            created_by=tenant["admin_user"].id,
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/telecaller/queue/today",
        headers={"Authorization": f"Bearer {tenant['telecaller_token']}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == len(payload["items"])
    assert payload["fresh_count"] == sum(item["source"] == "NEW_LEAD" for item in payload["items"])
    assert payload["followup_count"] == sum(item["source"] == "FOLLOWUP" for item in payload["items"])
    classification = {
        item["lead_id"]: item["source"]
        for item in payload["items"]
        if item["lead_id"] in {followup_lead.id, fresh_lead.id}
    }
    assert classification[followup_lead.id] == "FOLLOWUP"
    assert classification[fresh_lead.id] == "NEW_LEAD"


def test_telecaller_cannot_mutate_another_owners_followup(client, db_session, tenant_a_fixture):
    tenant = tenant_a_fixture
    other = User(
        organization_id=tenant["org"].id,
        tenant_role="TELECALLER",
        full_name="Follow-up Owner",
        email="followup.owner@alpha.com",
        password_hash=get_password_hash("Password@123"),
        status="ACTIVE",
    )
    db_session.add(other)
    db_session.commit()
    lead = create_lead(
        db_session,
        tenant["org"].id,
        LeadCreate(
            title="Restricted follow-up lead",
            pipeline_stage_id=tenant["org"].pipelines[0].stages[0].id,
            owner_id=other.id,
        ),
        tenant["admin_user"],
    )
    task = Task(
        organization_id=tenant["org"].id,
        lead_id=lead.id,
        task_type="FOLLOW_UP",
        title="Private callback",
        status="PENDING",
        priority="MEDIUM",
        due_at=datetime.now(timezone.utc),
        assigned_to=other.id,
        created_by=tenant["admin_user"].id,
    )
    db_session.add(task)
    db_session.commit()

    response = client.post(
        f"/api/v1/tasks/{task.id}/complete",
        headers={"Authorization": f"Bearer {tenant['telecaller_token']}"},
    )
    assert response.status_code == 404
    db_session.refresh(task)
    assert task.status == "PENDING"


def test_call_outcome_stage_and_no_followup_are_atomic(db_session, tenant_a_fixture):
    tenant = tenant_a_fixture
    lead = _assigned_lead(db_session, tenant, "Atomic outcome and stage lead")
    stages = tenant["org"].pipelines[0].stages
    target_stage = stages[1]

    create_activity(
        db_session,
        tenant["org"].id,
        tenant["telecaller_user"],
        ActivityCreate(
            lead_id=lead.id,
            activity_type="CALL",
            status="INTERESTED",
            description="Budget and timing discussed.",
            pipeline_stage_id=target_stage.id,
            followup_preset="none",
        ),
    )

    db_session.refresh(lead)
    assert lead.pipeline_stage_id == target_stage.id
    assert db_session.query(LeadStageHistory).filter(
        LeadStageHistory.lead_id == lead.id,
        LeadStageHistory.to_stage_id == target_stage.id,
    ).count() == 1
    assert db_session.query(CallRecord).filter(
        CallRecord.lead_id == lead.id,
        CallRecord.disposition == "INTERESTED",
    ).count() == 1
    assert db_session.query(Activity).filter(
        Activity.lead_id == lead.id,
        Activity.activity_type == "CALL",
        Activity.description == "Budget and timing discussed.",
    ).count() == 1
    assert db_session.query(Task).filter(
        Task.lead_id == lead.id,
        Task.task_type == "FOLLOW_UP",
        Task.status == "PENDING",
    ).count() == 0


def test_followup_api_and_worklist_share_accessible_active_population(client, db_session, tenant_a_fixture):
    tenant = tenant_a_fixture
    lead = _assigned_lead(db_session, tenant, "Future persisted follow-up")
    task = Task(
        organization_id=tenant["org"].id,
        lead_id=lead.id,
        task_type="FOLLOW_UP",
        title="Future callback",
        status="PENDING",
        priority="MEDIUM",
        due_at=datetime.now(timezone.utc) + timedelta(days=5),
        assigned_to=tenant["telecaller_user"].id,
        created_by=tenant["admin_user"].id,
    )
    db_session.add(task)
    db_session.commit()

    headers = {"Authorization": f"Bearer {tenant['telecaller_token']}"}
    followup_response = client.get("/api/v1/followups/", headers=headers)
    queue_response = client.get("/api/v1/telecaller/queue/today", headers=headers)
    assert followup_response.status_code == 200
    assert queue_response.status_code == 200

    followups = followup_response.json()
    queue_followups = [item for item in queue_response.json()["items"] if item["source"] == "FOLLOWUP"]
    assert {item["lead_id"] for item in followups} == {item["lead_id"] for item in queue_followups}
    projection = next(item for item in followups if item["id"] == task.id)
    assert projection["lead"]["id"] == lead.id
    assert projection["lead"]["title"] == "Future persisted follow-up"
    assert projection["display_status"] == "PENDING"
    assert projection["attempt_count"] == 0

    completed = client.post(f"/api/v1/followups/{task.id}/complete", headers=headers)
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"
    refreshed = client.get("/api/v1/followups/", headers=headers).json()
    assert task.id not in {item["id"] for item in refreshed}


def test_followup_max_attempts_closes_active_cycle(db_session, tenant_a_fixture):
    tenant = tenant_a_fixture
    lead = _assigned_lead(db_session, tenant, "Maximum attempt follow-up")
    db_session.add(FollowupPolicy(
        id=generate_uuid(),
        organization_id=tenant["org"].id,
        name="Callback max attempts",
        trigger_outcome="TEST_MAX_ATTEMPTS",
        max_attempts=2,
        interval_minutes=1440,
        is_active=True,
    ))
    db_session.commit()

    create_activity(
        db_session,
        tenant["org"].id,
        tenant["telecaller_user"],
        ActivityCreate(lead_id=lead.id, activity_type="CALL", status="TEST_MAX_ATTEMPTS", followup_preset="tomorrow"),
    )
    assert db_session.query(Task).filter(Task.lead_id == lead.id, Task.status == "PENDING").count() == 1

    for _ in range(2):
        create_activity(
            db_session,
            tenant["org"].id,
            tenant["telecaller_user"],
            ActivityCreate(lead_id=lead.id, activity_type="CALL", status="TEST_MAX_ATTEMPTS", followup_preset="tomorrow"),
        )

    assert db_session.query(Task).filter(Task.lead_id == lead.id, Task.status == "PENDING").count() == 0
    closed = db_session.query(Task).filter(Task.lead_id == lead.id, Task.status == "CANCELLED").one()
    assert "Maximum follow-up attempts reached (2)" in closed.description
