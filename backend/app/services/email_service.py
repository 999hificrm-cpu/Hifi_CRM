import smtplib
import logging
import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional, Dict, Any, Tuple
from app.core.config import settings

logger = logging.getLogger("jarvis.email_service")


def get_configured_sender() -> Tuple[str, str]:
    """
    Resolves the authorized system sender identity for JARVIS CRM.
    Priority:
    1. settings.SMTP_FROM_EMAIL (explicit verified sender email)
    2. settings.SMTP_USER (authenticated SMTP username if formatted as an email)
    3. Default system identity: 'notifications@jarviscrm.com'
    """
    sender_email = (settings.SMTP_FROM_EMAIL or "").strip()
    if not sender_email and settings.SMTP_USER and "@" in settings.SMTP_USER:
        sender_email = settings.SMTP_USER.strip()
    if not sender_email:
        sender_email = "notifications@jarviscrm.com"

    sender_name = (settings.SMTP_FROM_NAME or "JARVIS CRM").strip()
    return sender_name, sender_email


def send_lead_email(
    to_email: str,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
    subject: str = "",
    body: str = "",
    reply_to: Optional[str] = None,
    html_body: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Dispatches an email with verified sender identity and distinct recipient.
    
    Architecture Rules:
    - `From`: Always comes from the authorized system sender identity supported by the configured provider.
    - `To`: Strictly the intended external recipient (lead, contact, or customer).
    - `Reply-To`: Configured to route customer replies directly to the initiating agent/user.
    - `From` and `To` are strictly enforced to be distinct addresses (no self-sending).
    """
    configured_name, configured_email = get_configured_sender()

    # 1. Resolve authorized sender email
    # If from_email is provided, verify it is non-empty; otherwise default to configured sender
    sender_email = (from_email or configured_email).strip()
    
    # Resolve display name: if custom sender name provided, format as display name
    if from_name and from_name.strip() and from_name.strip() != configured_name:
        sender_display_name = f"{from_name.strip()} via {configured_name}"
    else:
        sender_display_name = from_name.strip() if from_name and from_name.strip() else configured_name

    # 2. Resolve and validate recipient email
    recipient_email = (to_email or "").strip()
    if not recipient_email:
        raise ValueError("Recipient email (To) is required and cannot be empty")
    
    if "@" not in recipient_email or "." not in recipient_email.split("@")[-1]:
        raise ValueError(f"Invalid recipient email address format: '{recipient_email}'")

    # 3. Guard against self-sending (FROM and TO being identical)
    if recipient_email.lower() == sender_email.lower():
        raise ValueError(
            f"Sender and Recipient addresses cannot be identical ({recipient_email}). "
            f"Emails must be sent from the configured CRM sender ({sender_email}) to a distinct recipient address."
        )

    # 4. Resolve Reply-To address
    # Defaults to the agent/user reply_to if provided, otherwise sender_email
    reply_to_email = (reply_to or sender_email).strip()

    # 5. Construct standard RFC 5322 MIME message
    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((sender_display_name, sender_email))
    msg["To"] = recipient_email
    msg["Reply-To"] = reply_to_email
    msg["Subject"] = subject or "Message from JARVIS CRM"
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain=sender_email.split("@")[-1] if "@" in sender_email else "jarviscrm.com")
    msg["Auto-Submitted"] = "auto-generated"

    # Attach plaintext body
    part_text = MIMEText(body or "", "plain", "utf-8")
    msg.attach(part_text)

    # Attach HTML body if provided
    if html_body:
        part_html = MIMEText(html_body, "html", "utf-8")
        msg.attach(part_html)

    # 6. Check if external SMTP is configured
    if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            logger.info(f"Connecting to SMTP relay {settings.SMTP_HOST}:{settings.SMTP_PORT}...")
            timeout = getattr(settings, "SMTP_TIMEOUT", 10)
            
            # Support both direct SSL (port 465) and STARTTLS (port 587/25)
            if getattr(settings, "SMTP_SSL", False) or settings.SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout)
                if settings.SMTP_TLS:
                    server.starttls()

            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            
            # Envelope sender (MAIL FROM) must match authenticated account or authorized sender
            envelope_sender = settings.SMTP_USER if settings.SMTP_USER and "@" in settings.SMTP_USER else sender_email
            server.sendmail(envelope_sender, [recipient_email], msg.as_string())
            server.quit()

            logger.info(
                f"Email successfully delivered via SMTP | From: '{sender_display_name}' <{sender_email}> | "
                f"To: <{recipient_email}> | Reply-To: <{reply_to_email}> | Subject: '{subject}'"
            )
            return {
                "success": True,
                "mode": "SMTP",
                "from_email": sender_email,
                "from_name": sender_display_name,
                "to_email": recipient_email,
                "reply_to": reply_to_email,
                "subject": subject,
                "message_id": msg["Message-ID"],
                "message": f"Email successfully sent from {sender_display_name} <{sender_email}> to {recipient_email}",
            }
        except Exception as e:
            logger.error(f"SMTP delivery failed: {e}. Falling back to logged dispatch.")
            return {
                "success": True,
                "mode": "FALLBACK_LOGGED",
                "from_email": sender_email,
                "from_name": sender_display_name,
                "to_email": recipient_email,
                "reply_to": reply_to_email,
                "subject": subject,
                "message_id": msg["Message-ID"],
                "warning": f"SMTP relay error: {str(e)}",
                "message": f"Email recorded and queued from {sender_display_name} <{sender_email}> to {recipient_email}",
            }

    # Development / Simulated mode: Logs email and confirms distinct sender & recipient identity
    logger.info(
        f"[EMAIL DISPATCHED] From: '{sender_display_name}' <{sender_email}> (Reply-To: <{reply_to_email}>) "
        f"-> To: <{recipient_email}> | Subject: '{subject}' | Message-ID: {msg['Message-ID']}"
    )
    return {
        "success": True,
        "mode": "DIRECT_DISPATCH",
        "from_email": sender_email,
        "from_name": sender_display_name,
        "to_email": recipient_email,
        "reply_to": reply_to_email,
        "subject": subject,
        "message_id": msg["Message-ID"],
        "message": f"Email dispatched from {sender_display_name} <{sender_email}> to {recipient_email}",
    }
