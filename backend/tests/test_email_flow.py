import email
import socket
import threading
import time
from email.message import EmailMessage
import pytest
from app.core.config import settings
from app.services.email_service import send_lead_email, get_configured_sender
from app.models.lead import Lead
from app.models.activity import Activity
from app.models.organization import Organization
from app.models.user import User


class MockSMTPServer(threading.Thread):
    """
    Lightweight RFC 5321 Mock SMTP Server running in a background thread.
    Records raw envelope commands (EHLO, MAIL FROM, RCPT TO, DATA) and parsed MIME message.
    """
    def __init__(self):
        super().__init__(daemon=True)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("127.0.0.1", 0))
        self.port = self.server_socket.getsockname()[1]
        self.server_socket.listen(5)
        self.received_messages = []
        self.received_envelopes = []
        self.running = True

    def run(self):
        while self.running:
            try:
                self.server_socket.settimeout(0.5)
                client_sock, _ = self.server_socket.accept()
            except socket.timeout:
                continue
            except Exception:
                break

            try:
                client_sock.sendall(b"220 127.0.0.1 Mock SMTP Service Ready\r\n")
                envelope = {"mail_from": None, "rcpt_to": []}
                data_mode = False
                data_buffer = []

                while True:
                    line = b""
                    while not line.endswith(b"\r\n"):
                        chunk = client_sock.recv(1)
                        if not chunk:
                            break
                        line += chunk
                    if not line:
                        break

                    text = line.decode("utf-8", errors="replace")

                    if data_mode:
                        if text == ".\r\n":
                            raw_email = "".join(data_buffer)
                            parsed = email.message_from_string(raw_email)
                            self.received_messages.append(parsed)
                            self.received_envelopes.append(envelope)
                            client_sock.sendall(b"250 2.0.0 Ok: queued\r\n")
                            data_mode = False
                        else:
                            data_buffer.append(text)
                        continue

                    cmd = text.strip().upper()
                    if cmd.startswith("EHLO") or cmd.startswith("HELO"):
                        client_sock.sendall(b"250-127.0.0.1 Hello\r\n250-AUTH PLAIN LOGIN\r\n250 OK\r\n")
                    elif cmd.startswith("AUTH LOGIN"):
                        client_sock.sendall(b"334 VXNlcm5hbWU6\r\n")  # Username prompt
                    elif cmd.startswith("AUTH PLAIN"):
                        client_sock.sendall(b"235 2.7.0 Authentication successful\r\n")
                    elif cmd == "QUIT":
                        client_sock.sendall(b"221 2.0.0 Bye\r\n")
                        break
                    elif cmd.startswith("MAIL FROM:"):
                        sender = text.strip()[10:].strip("<> ")
                        envelope["mail_from"] = sender
                        client_sock.sendall(b"250 2.1.0 Sender OK\r\n")
                    elif cmd.startswith("RCPT TO:"):
                        rcpt = text.strip()[8:].strip("<> ")
                        envelope["rcpt_to"].append(rcpt)
                        client_sock.sendall(b"250 2.1.5 Recipient OK\r\n")
                    elif cmd == "DATA":
                        data_mode = True
                        data_buffer = []
                        client_sock.sendall(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                    elif len(cmd) > 0:
                        # Handle base64 auth prompts or generic success
                        client_sock.sendall(b"235 2.7.0 Authentication successful\r\n")
            except Exception:
                pass
            finally:
                client_sock.close()

    def close(self):
        self.running = False
        try:
            self.server_socket.close()
        except Exception:
            pass


def test_get_configured_sender_fallback():
    name, email_addr = get_configured_sender()
    assert email_addr is not None
    assert "@" in email_addr
    assert name is not None


def test_send_lead_email_distinct_from_and_to():
    """
    Verifies send_lead_email constructs valid RFC 5322 MIME messages with:
    - Sender = configured authorized sender identity
    - Recipient = intended lead/customer
    - Reply-To = initiating user/agent
    - From != To
    """
    configured_name, configured_email = get_configured_sender()
    lead_recipient = "prospect.client@externalcompany.com"
    agent_email = "sarah.agent@jarviscrm.com"

    result = send_lead_email(
        to_email=lead_recipient,
        from_email=configured_email,
        from_name="Sarah Agent",
        reply_to=agent_email,
        subject="Exclusive Partnership Proposal",
        body="Hello, we would love to discuss a partnership with your team."
    )

    assert result["success"] is True
    assert result["from_email"] == configured_email
    assert result["to_email"] == lead_recipient
    assert result["reply_to"] == agent_email
    # CRITICAL: From and To MUST be completely different addresses
    assert result["from_email"].lower() != result["to_email"].lower()
    assert "Sarah Agent via" in result["from_name"] or result["from_name"] == "Sarah Agent"
    assert "message_id" in result
    assert result["message_id"].startswith("<")


def test_send_lead_email_self_send_prevention():
    """
    Verifies that attempting to send an email where recipient is identical to
    the sender is strictly blocked with a ValueError.
    """
    configured_name, configured_email = get_configured_sender()

    with pytest.raises(ValueError) as excinfo:
        send_lead_email(
            to_email=configured_email,  # Same as sender
            from_email=configured_email,
            subject="Test Self Send",
            body="This should not be allowed"
        )
    assert "Sender and Recipient addresses cannot be identical" in str(excinfo.value)


def test_send_lead_email_invalid_recipient():
    """
    Verifies that malformed or empty recipient addresses are rejected.
    """
    with pytest.raises(ValueError):
        send_lead_email(to_email="", subject="Subject", body="Body")

    with pytest.raises(ValueError):
        send_lead_email(to_email="notanemail", subject="Subject", body="Body")


def test_real_smtp_delivery_and_header_verification(monkeypatch):
    """
    Starts an in-memory Mock SMTP Server, configures settings to point to it,
    dispatches an email via send_lead_email, and inspects the raw received
    MIME headers and SMTP envelope to confirm From and To are distinct.
    """
    mock_server = MockSMTPServer()
    mock_server.start()
    time.sleep(0.1)

    try:
        sender_email = "notifications@jarviscrm.com"
        sender_name = "JARVIS CRM"
        recipient_email = "lead.customer@corporate.org"
        agent_reply_to = "agent.smith@jarviscrm.com"

        # Configure settings for mock SMTP
        monkeypatch.setattr(settings, "SMTP_HOST", "127.0.0.1")
        monkeypatch.setattr(settings, "SMTP_PORT", mock_server.port)
        monkeypatch.setattr(settings, "SMTP_USER", "smtp_user@jarviscrm.com")
        monkeypatch.setattr(settings, "SMTP_PASSWORD", "mock_secret")
        monkeypatch.setattr(settings, "SMTP_TLS", False)
        monkeypatch.setattr(settings, "SMTP_SSL", False)
        monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", sender_email)
        monkeypatch.setattr(settings, "SMTP_FROM_NAME", sender_name)

        result = send_lead_email(
            to_email=recipient_email,
            from_name="Agent Smith",
            reply_to=agent_reply_to,
            subject="Regarding your inquiry",
            body="Thank you for reaching out to us."
        )

        assert result["success"] is True
        assert result["mode"] == "SMTP"
        assert result["from_email"] == sender_email
        assert result["to_email"] == recipient_email
        assert result["from_email"] != result["to_email"]

        # Wait for SMTP delivery
        time.sleep(0.2)
        assert len(mock_server.received_messages) == 1
        msg = mock_server.received_messages[0]

        # Verify parsed MIME headers received by SMTP server
        parsed_from = msg.get("From")
        parsed_to = msg.get("To")
        parsed_reply_to = msg.get("Reply-To")
        parsed_subject = msg.get("Subject")

        assert sender_email in parsed_from
        assert parsed_to == recipient_email
        assert parsed_reply_to == agent_reply_to
        assert parsed_subject == "Regarding your inquiry"

        # Verify Envelope recipients
        envelope = mock_server.received_envelopes[0]
        assert recipient_email in envelope["rcpt_to"]
        assert envelope["mail_from"] == "smtp_user@jarviscrm.com"

        # Confirm FROM and TO headers received over wire are distinct
        assert parsed_from != parsed_to
        assert sender_email != recipient_email

    finally:
        mock_server.close()


def test_api_dispatch_lead_email(client, db_session, tenant_a_fixture):
    """
    Tests the full API endpoint POST /api/v1/leads/{lead_id}/send-email
    Verifies that:
    - The API accepts the request and sends from the authorized system identity.
    - Reply-To is set to the authenticated admin/agent email.
    - To is set to the lead's contact email.
    - An activity log is recorded with matching From and To details.
    """
    org = tenant_a_fixture["org"]
    admin = tenant_a_fixture["admin_user"]
    token = tenant_a_fixture["admin_token"]
    stage = org.pipelines[0].stages[0]

    # 2. Create a test lead with a distinct recipient contact email
    test_lead = Lead(
        organization_id=org.id,
        title="Enterprise Expansion Project",
        company_name="Global Logistics Ltd",
        contact_name="Rajesh Kumar",
        contact_email="rajesh.kumar@globallogistics.in",
        pipeline_stage_id=stage.id,
        status="OPEN",
        score=75
    )
    db_session.add(test_lead)
    db_session.commit()
    db_session.refresh(test_lead)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": org.id
    }

    # 3. Call dispatch email API
    payload = {
        "subject": "Discussion on Logistics Automation",
        "body": "Hi Rajesh, following up on our recent conversation.",
        "to_email": "rajesh.kumar@globallogistics.in"
    }

    res = client.post(f"/api/v1/leads/{test_lead.id}/send-email", json=payload, headers=headers)
    assert res.status_code == 200, f"Dispatch failed: {res.text}"
    data = res.json()

    assert data["status"] == "success"
    result = data["result"]

    # Verify FROM, TO, Reply-To
    assert result["from_email"] == "notifications@jarviscrm.com"
    assert result["to_email"] == "rajesh.kumar@globallogistics.in"
    assert result["reply_to"] == admin.email
    assert result["from_email"] != result["to_email"]

    # 4. Verify Activity recorded in DB
    activity = db_session.query(Activity).filter(
        Activity.lead_id == test_lead.id,
        Activity.activity_type == "EMAIL"
    ).first()
    assert activity is not None
    assert "notifications@jarviscrm.com" in activity.description
    assert "rajesh.kumar@globallogistics.in" in activity.description
    assert admin.email in activity.description


def test_api_dispatch_lead_email_self_send_blocked(client, db_session, tenant_a_fixture):
    """
    Verifies that calling the API with the system sender as recipient is rejected with 400.
    """
    org = tenant_a_fixture["org"]
    token = tenant_a_fixture["admin_token"]
    stage = org.pipelines[0].stages[0]

    test_lead = Lead(
        organization_id=org.id,
        title="Self Send Test Lead",
        company_name="Self Corp",
        contact_name="Admin Duplicate",
        contact_email="notifications@jarviscrm.com",  # Identical to system sender
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

    res = client.post(
        f"/api/v1/leads/{test_lead.id}/send-email",
        json={"subject": "Test", "body": "Body", "to_email": "notifications@jarviscrm.com"},
        headers=headers
    )
    assert res.status_code == 400
    assert "cannot be identical to the system sender email" in res.json()["detail"]
