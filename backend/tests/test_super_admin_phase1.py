import pytest
from datetime import datetime, timezone
from app.models.organization import Organization
from app.models.user import User
from app.models.lead import Lead
from app.models.audit import AuditLog
from app.models.rbac import PlatformRole, Permission, seed_platform_rbac
from app.models.support import SupportSession
from app.services.audit_service import audit_service
from app.core.security import create_access_token


@pytest.fixture(autouse=True)
def ensure_rbac_seeded(db_session):
    seed_platform_rbac(db_session)


def test_platform_rbac_permissions_and_hierarchy(client, db_session, tenant_a_fixture):
    """Test Problem #16, #17: Platform permissions and role-based checks."""
    admin_user = tenant_a_fixture["admin_user"]

    # 1. Create a Support Admin user and a Billing Admin user
    support_admin = User(
        full_name="Sam Support",
        email="sam.support@jarvis.com",
        password_hash="fakehash",
        platform_role="SUPPORT_ADMIN",
        status="ACTIVE"
    )
    billing_admin = User(
        full_name="Bill Billing",
        email="bill.billing@jarvis.com",
        password_hash="fakehash",
        platform_role="BILLING_ADMIN",
        status="ACTIVE"
    )
    db_session.add_all([support_admin, billing_admin])
    db_session.commit()

    # Check permission resolution on User model
    support_perms = support_admin.get_effective_platform_permissions(db=db_session)
    assert "PLATFORM_SUPPORT" in support_perms
    assert "PLATFORM_BILLING_WRITE" not in support_perms

    billing_perms = billing_admin.get_effective_platform_permissions(db=db_session)
    assert "PLATFORM_BILLING_WRITE" in billing_perms
    assert "PLATFORM_SUPPORT" not in billing_perms

    # Create tokens
    support_token = create_access_token(subject=support_admin.id, token_version=1)
    billing_token = create_access_token(subject=billing_admin.id, token_version=1)

    # Support admin can access support sessions list
    resp = client.get("/api/v1/admin/support/sessions", headers={"Authorization": f"Bearer {support_token}"})
    assert resp.status_code == 200

    # Billing admin cannot access support sessions list (requires PLATFORM_SUPPORT)
    resp = client.get("/api/v1/admin/support/sessions", headers={"Authorization": f"Bearer {billing_token}"})
    assert resp.status_code == 403


def test_role_assignment_and_permission_override_auditing(client, db_session, tenant_a_fixture):
    """Test Problem #18: RBAC changes generate audited events with actor and target."""
    super_admin = User(
        full_name="Master Admin",
        email="master@jarvis.com",
        password_hash="fakehash",
        platform_role="SUPER_ADMIN",
        status="ACTIVE"
    )
    test_user = User(
        full_name="New Staff",
        email="staff@jarvis.com",
        password_hash="fakehash",
        platform_role="DATA_ADMIN",
        status="ACTIVE"
    )
    db_session.add_all([super_admin, test_user])
    db_session.commit()

    super_token = create_access_token(subject=super_admin.id, token_version=1)
    headers = {"Authorization": f"Bearer {super_token}"}

    # 1. Assign new role PLATFORM_ADMIN
    resp = client.post("/api/v1/admin/access/assign-role", json={
        "user_id": test_user.id,
        "role_code": "PLATFORM_ADMIN",
        "reason": "Promoted to platform admin"
    }, headers=headers)
    assert resp.status_code == 200
    db_session.refresh(test_user)
    assert test_user.platform_role == "PLATFORM_ADMIN"
    assert test_user.token_version > 1  # Session bumped

    # Verify audit record
    audit = db_session.query(AuditLog).filter(
        AuditLog.action == "ROLE_ASSIGNED",
        AuditLog.entity_id == test_user.id
    ).first()
    assert audit is not None
    assert audit.actor_user_id == super_admin.id
    assert audit.target_user_id == test_user.id
    assert audit.new_values["platform_role"] == "PLATFORM_ADMIN"

    # 2. Grant explicit permission override
    resp2 = client.post("/api/v1/admin/access/permission-override", json={
        "user_id": test_user.id,
        "permission_code": "PLATFORM_BILLING_WRITE",
        "granted": True,
        "reason": "Special project access"
    }, headers=headers)
    assert resp2.status_code == 200
    db_session.refresh(test_user)
    assert test_user.permission_overrides.get("PLATFORM_BILLING_WRITE") is True

    # Check that test_user now has this permission
    perms = test_user.get_effective_platform_permissions(db=db_session)
    assert "PLATFORM_BILLING_WRITE" in perms


def test_support_session_context_and_audit_isolation(client, db_session, tenant_a_fixture):
    """Test Problems #19, #20, #46: Explicit support session and dual-identity auditing."""
    org = tenant_a_fixture["org"]
    telecaller = tenant_a_fixture["telecaller_user"]

    support_agent = User(
        full_name="Agent Smith",
        email="smith.support@jarvis.com",
        password_hash="fakehash",
        platform_role="SUPPORT_ADMIN",
        status="ACTIVE"
    )
    db_session.add(support_agent)
    db_session.commit()

    agent_token = create_access_token(subject=support_agent.id, token_version=1)

    # 1. Create short-lived support session (requires reason)
    resp = client.post("/api/v1/admin/support/session", json={
        "organization_id": org.id,
        "target_user_id": telecaller.id,
        "reason": "Troubleshooting missing call records for customer",
        "duration_minutes": 15
    }, headers={"Authorization": f"Bearer {agent_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "support_token" in data
    support_token = data["support_token"]
    session_id = data["id"]

    # 2. Make tenant request using support token (without X-Tenant-Id header)
    resp2 = client.get("/api/v1/leads/", headers={"Authorization": f"Bearer {support_token}"})
    assert resp2.status_code == 200

    # 3. Create a lead using support token and verify dual identity audit
    lead_resp = client.post("/api/v1/leads/", json={
        "title": "Support Created Lead",
        "company_name": "Test Support Corp"
    }, headers={"Authorization": f"Bearer {support_token}"})
    assert lead_resp.status_code in (200, 201)
    created_lead_id = lead_resp.json()["id"]


    # Verify audit record in audit service
    audit = db_session.query(AuditLog).filter(
        AuditLog.action == "SUPPORT_SESSION_CREATED",
        AuditLog.support_session_id == session_id
    ).first()
    assert audit is not None
    assert audit.actor_user_id == support_agent.id
    assert audit.target_user_id == telecaller.id
    assert audit.organization_id == org.id

    # 4. Revoke support session
    revoke_resp = client.post(f"/api/v1/admin/support/session/{session_id}/revoke", headers={"Authorization": f"Bearer {agent_token}"})
    assert revoke_resp.status_code == 200

    # Subsequent requests using the revoked support token MUST be rejected
    blocked_resp = client.get("/api/v1/leads/", headers={"Authorization": f"Bearer {support_token}"})
    assert blocked_resp.status_code in (401, 403)


def test_session_token_revocation_on_suspension(client, db_session):
    """Test Problems #15, #18: Immediate token revocation when token_version increments."""
    temp_user = User(
        full_name="Revocable User",
        email="revocable@test.local",
        password_hash="fakehash",
        status="ACTIVE",
        token_version=1
    )
    db_session.add(temp_user)
    db_session.commit()

    user_token = create_access_token(subject=temp_user.id, token_version=temp_user.token_version or 1)

    # User can access /auth/me initially
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 200

    # Create Super Admin
    super_admin = User(
        full_name="Platform Boss",
        email="boss@jarvis.com",
        password_hash="fakehash",
        platform_role="SUPER_ADMIN",
        status="ACTIVE"
    )
    db_session.add(super_admin)
    db_session.commit()
    admin_token = create_access_token(subject=super_admin.id, token_version=1)

    # Revoke sessions for this user
    revoke_resp = client.post("/api/v1/admin/access/revoke-sessions", json={
        "user_id": temp_user.id,
        "reason": "Suspicious login detected"
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert revoke_resp.status_code == 200

    # The previous token MUST now be immediately rejected (401)
    blocked_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert blocked_resp.status_code == 401


def test_organization_suspension_revokes_all_tenant_sessions(client, db_session):
    """Test Problems #9, #15, #50: Suspending organization invalidates all tenant user sessions."""
    separate_org = Organization(name="Phase1 Temp Org", slug="phase1-temp-org", status="ACTIVE")
    db_session.add(separate_org)
    db_session.commit()

    admin = User(
        organization_id=separate_org.id,
        tenant_role="ORG_ADMIN",
        full_name="Temp Admin",
        email="tempadmin@phase1.com",
        password_hash="fakehash",
        status="ACTIVE",
        token_version=1
    )
    telecaller = User(
        organization_id=separate_org.id,
        tenant_role="TELECALLER",
        full_name="Temp TC",
        email="temptc@phase1.com",
        password_hash="fakehash",
        status="ACTIVE",
        token_version=1
    )
    db_session.add_all([admin, telecaller])
    db_session.commit()

    admin_token = create_access_token(subject=admin.id, token_version=admin.token_version or 1)
    tc_token = create_access_token(subject=telecaller.id, token_version=telecaller.token_version or 1)

    super_admin = User(
        full_name="Platform Chief",
        email="chief@jarvis.com",
        password_hash="fakehash",
        platform_role="SUPER_ADMIN",
        status="ACTIVE"
    )
    db_session.add(super_admin)
    db_session.commit()
    boss_token = create_access_token(subject=super_admin.id, token_version=1)

    # Suspend organization with reason and Idempotency-Key
    suspend_resp = client.post(
        f"/api/v1/admin/organizations/{separate_org.id}/suspend",
        json={"reason": "Non-payment of Enterprise invoice #INV-900"},
        headers={"Authorization": f"Bearer {boss_token}", "Idempotency-Key": "idemp-suspend-001"}
    )
    assert suspend_resp.status_code == 200
    data = suspend_resp.json()
    assert data["status"] == "SUSPENDED"

    # Repeated request with same Idempotency-Key returns cached response
    repeat_resp = client.post(
        f"/api/v1/admin/organizations/{separate_org.id}/suspend",
        json={"reason": "Non-payment of Enterprise invoice #INV-900"},
        headers={"Authorization": f"Bearer {boss_token}", "Idempotency-Key": "idemp-suspend-001"}
    )
    assert repeat_resp.status_code == 200
    assert repeat_resp.json() == data

    # Both tenant users' tokens must now be rejected
    r1 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert r1.status_code in (401, 403)

    r2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tc_token}"})
    assert r2.status_code in (401, 403)


def test_tamper_evident_audit_hash_chain(db_session, tenant_a_fixture):
    """Test Problems #22, #23, #24: SHA-256 hash chaining and chain verification."""
    org = tenant_a_fixture["org"]
    admin = tenant_a_fixture["admin_user"]

    # Record consecutive audit events
    log1 = audit_service.record(
        db=db_session,
        action="TEST_ACTION_1",
        entity_type="ORGANIZATION",
        entity_id=org.id,
        actor_user_id=admin.id,
        organization_id=org.id,
        new_values={"val": 1}
    )
    assert log1.event_hash is not None

    log2 = audit_service.record(
        db=db_session,
        action="TEST_ACTION_2",
        entity_type="ORGANIZATION",
        entity_id=org.id,
        actor_user_id=admin.id,
        organization_id=org.id,
        new_values={"val": 2}
    )
    assert log2.previous_event_hash == log1.event_hash

    log3 = audit_service.record(
        db=db_session,
        action="TEST_ACTION_3",
        entity_type="ORGANIZATION",
        entity_id=org.id,
        actor_user_id=admin.id,
        organization_id=org.id,
        new_values={"val": 3}
    )
    assert log3.previous_event_hash == log2.event_hash

    # Verify integrity of chain
    verify_res = audit_service.verify_chain(db=db_session, limit=100)
    assert verify_res["status"] == "VALID"
    assert verify_res["verified_count"] >= 3


def test_soft_delete_and_recycle_bin_recovery(client, db_session, tenant_a_fixture):
    """Test Problems #10, #41, #42: Soft delete, recycle bin listing, and restore."""
    org = tenant_a_fixture["org"]
    admin = tenant_a_fixture["admin_user"]
    db_session.refresh(org)
    org.status = "ACTIVE"
    db_session.refresh(admin)
    admin.status = "ACTIVE"
    db_session.commit()



    admin_token = create_access_token(subject=admin.id, token_version=admin.token_version or 1)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}


    # 1. Create a lead
    from app.models.pipeline import PipelineStage
    stage = db_session.query(PipelineStage).join(PipelineStage.pipeline).filter(
        PipelineStage.pipeline.has(organization_id=org.id)
    ).first()
    assert stage is not None

    lead = Lead(
        organization_id=org.id,
        title="Accidental Delete Lead",
        company_name="Delete Corp",
        pipeline_stage_id=stage.id,
        status="OPEN"
    )
    db_session.add(lead)
    db_session.commit()
    lead_id = lead.id


    # 2. Soft delete the lead via DELETE /leads/{id}
    del_resp = client.delete(f"/api/v1/leads/{lead_id}?reason=Accidental+deletion", headers=admin_headers)
    assert del_resp.status_code == 200

    # Lead should not appear in regular leads list
    list_resp = client.get("/api/v1/leads/", headers=admin_headers)
    assert list_resp.status_code == 200
    lead_ids = [l["id"] for l in list_resp.json()]
    assert lead_id not in lead_ids

    # 3. Super Admin inspects Recycle Bin
    super_admin = User(
        full_name="Recycle Admin",
        email="recycle@jarvis.com",
        password_hash="fakehash",
        platform_role="SUPER_ADMIN",
        status="ACTIVE"
    )
    db_session.add(super_admin)
    db_session.commit()
    super_token = create_access_token(subject=super_admin.id, token_version=1)
    super_headers = {"Authorization": f"Bearer {super_token}"}

    bin_resp = client.get("/api/v1/admin/recovery/leads", headers=super_headers)
    assert bin_resp.status_code == 200
    bin_items = bin_resp.json()
    bin_ids = [item["id"] for item in bin_items]
    assert lead_id in bin_ids

    # 4. Restore the lead from Recycle Bin
    restore_resp = client.post(
        f"/api/v1/admin/recovery/leads/{lead_id}/restore",
        json={"reason": "Customer called requesting reactivation"},
        headers=super_headers
    )
    assert restore_resp.status_code == 200

    # Lead should now be visible again in regular tenant leads query
    list_again = client.get("/api/v1/leads/", headers=admin_headers)
    assert list_again.status_code == 200
    restored_ids = [l["id"] for l in list_again.json()]
    assert lead_id in restored_ids
