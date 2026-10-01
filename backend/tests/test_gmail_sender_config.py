import urllib.parse
import pytest
from app.models.lead import Lead
from app.models.organization import Organization


def test_gmail_action_uses_configured_authorized_sender(client, db_session, tenant_a_fixture):
    """
    Verifies that the /leads/{id}/action/email endpoint generates a Gmail compose URL
    using the configured authorized sender identity (via /mail/u/{sender}/ and authuser={sender})
    while strictly avoiding any invalid/spoofed from= URL parameters and preserving recipient to,
    subject, and body.
    """
    org = tenant_a_fixture["org"]
    token = tenant_a_fixture["admin_token"]
    stage = org.pipelines[0].stages[0]

    test_lead = Lead(
        organization_id=org.id,
        title="Gmail Send-As Routing Lead",
        company_name="Acme Tech",
        contact_name="Priya Sharma",
        contact_email="priya.sharma@acmetech.com",
        pipeline_stage_id=stage.id,
        status="OPEN"
    )
    db_session.add(test_lead)
    db_session.commit()
    db_session.refresh(test_lead)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": org.id
    }

    res = client.post(f"/api/v1/leads/{test_lead.id}/action/email", headers=headers)
    assert res.status_code == 200, f"Failed: {res.text}"
    data = res.json()

    assert data["status"] == "success"
    assert data["action_type"] == "email"
    assert data["recipient_email"] == "priya.sharma@acmetech.com"

    gmail_url = data["gmail_url"]
    assert gmail_url is not None
    assert "mail.google.com/mail/u/" in gmail_url

    parsed = urllib.parse.urlparse(gmail_url)
    qs = urllib.parse.parse_qs(parsed.query)

    # 1. Anti-spoofing rule: strictly NO 'from' parameter in Gmail compose URL
    assert "from" not in qs, "Gmail compose URL must not inject an arbitrary 'from' query parameter"

    # 2. Preserved recipient logic: 'to' must match lead's contact email
    assert qs.get("to") == ["priya.sharma@acmetech.com"]

    # 3. Subject and Body preserved
    assert "su" in qs
    assert "body" in qs
    assert "Priya Sharma" in qs["body"][0]

    # 4. Authorized sender identity session routing
    assert "authuser" in qs
    authorized_sender = qs["authuser"][0]
    assert "@" in authorized_sender
    # Check that session path matches authuser
    assert f"/mail/u/{urllib.parse.quote(authorized_sender)}" in parsed.path or f"/mail/u/{authorized_sender}" in parsed.path


def test_gmail_action_uses_org_settings_authorized_sender(client, db_session, tenant_a_fixture):
    """
    Verifies that when an organization configures an authorized_sender_email in settings,
    the Gmail compose session explicitly routes to that authorized sender identity.
    """
    org = tenant_a_fixture["org"]
    token = tenant_a_fixture["admin_token"]
    stage = org.pipelines[0].stages[0]

    # Configure custom authorized sender in organization settings
    custom_sender = "sales.team@apexlogistics.com"
    org.settings = {"authorized_sender_email": custom_sender}
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    test_lead = Lead(
        organization_id=org.id,
        title="Custom Sender Org Lead",
        company_name="Enterprise Corp",
        contact_name="Amit Patel",
        contact_email="amit.patel@enterprisecorp.io",
        pipeline_stage_id=stage.id,
        status="OPEN"
    )
    db_session.add(test_lead)
    db_session.commit()
    db_session.refresh(test_lead)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": org.id
    }

    res = client.post(f"/api/v1/leads/{test_lead.id}/action/email", headers=headers)
    assert res.status_code == 200, f"Failed: {res.text}"
    data = res.json()

    gmail_url = data["gmail_url"]
    parsed = urllib.parse.urlparse(gmail_url)
    qs = urllib.parse.parse_qs(parsed.query)

    # Must route to custom authorized sender
    assert qs.get("authuser") == [custom_sender]
    assert custom_sender in urllib.parse.unquote(parsed.path)
    assert qs.get("to") == ["amit.patel@enterprisecorp.io"]
    assert "from" not in qs


def test_gmail_action_missing_recipient_validation(client, db_session, tenant_a_fixture):
    """
    Verifies that leads without a recipient email return a 400 error rather than sending to empty.
    """
    org = tenant_a_fixture["org"]
    token = tenant_a_fixture["admin_token"]
    stage = org.pipelines[0].stages[0]

    test_lead = Lead(
        organization_id=org.id,
        title="No Email Lead",
        company_name="Anonymous Corp",
        contact_name="Unknown",
        contact_email=None,
        pipeline_stage_id=stage.id,
        status="OPEN"
    )
    db_session.add(test_lead)
    db_session.commit()
    db_session.refresh(test_lead)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": org.id
    }

    res = client.post(f"/api/v1/leads/{test_lead.id}/action/email", headers=headers)
    assert res.status_code == 400
    assert "recipient contact email" in res.json()["detail"]
