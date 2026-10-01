"""
Gmail API Service for JARVIS CRM.

Provides OAuth2 authentication flow and email sending via Gmail API
using verified Send-As identities. This replaces the previous approach
of generating Gmail compose URLs (which cannot control the From address).

Architecture:
  1. User connects their Google account via OAuth2 consent flow
  2. JARVIS stores access_token + refresh_token on the user record
  3. When sending, JARVIS validates the configured sender is a verified
     Send-As identity on the connected Google account
  4. Email is sent via Gmail API (users.messages.send) with the verified
     Send-As identity as the From address
"""

import base64
import logging
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlencode

import httpx

from app.core.config import settings

logger = logging.getLogger("jarvis.gmail_service")

# Gmail API scopes required
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://www.googleapis.com/auth/userinfo.email",
]

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"


def is_gmail_configured() -> bool:
    """Check if Google OAuth2 credentials are configured."""
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def get_oauth_authorization_url(user_id: str) -> str:
    """
    Generate the Google OAuth2 consent URL.
    The user_id is embedded in the state parameter for the callback.
    """
    if not is_gmail_configured():
        raise ValueError(
            "Google OAuth2 credentials not configured. "
            "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env"
        )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": user_id,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_oauth_code(code: str) -> Dict[str, Any]:
    """
    Exchange an authorization code for access and refresh tokens.
    Returns: {"access_token": ..., "refresh_token": ..., "expires_in": ..., "token_type": ...}
    """
    if not is_gmail_configured():
        raise ValueError("Google OAuth2 credentials not configured.")

    payload = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    with httpx.Client(timeout=15) as client:
        resp = client.post(GOOGLE_TOKEN_URL, data=payload)
        if resp.status_code != 200:
            logger.error(f"Google token exchange failed: {resp.status_code} {resp.text}")
            raise ValueError(f"Failed to exchange OAuth code: {resp.text}")
        token_data = resp.json()

    # Fetch the authenticated user's email
    access_token = token_data["access_token"]
    email = _get_authenticated_email(access_token)

    return {
        "access_token": access_token,
        "refresh_token": token_data.get("refresh_token"),
        "expires_at": int(time.time()) + token_data.get("expires_in", 3600),
        "email": email,
    }


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """Refresh an expired access token using the refresh token."""
    if not is_gmail_configured():
        raise ValueError("Google OAuth2 credentials not configured.")

    payload = {
        "refresh_token": refresh_token,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "grant_type": "refresh_token",
    }

    with httpx.Client(timeout=15) as client:
        resp = client.post(GOOGLE_TOKEN_URL, data=payload)
        if resp.status_code != 200:
            logger.error(f"Google token refresh failed: {resp.status_code} {resp.text}")
            raise ValueError(f"Failed to refresh access token: {resp.text}")
        data = resp.json()

    return {
        "access_token": data["access_token"],
        "expires_at": int(time.time()) + data.get("expires_in", 3600),
    }


def get_valid_access_token(gmail_tokens: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Returns a valid access token, refreshing if expired.
    Returns (access_token, updated_tokens_dict).
    The caller should persist updated_tokens_dict if it changed.
    """
    if not gmail_tokens:
        raise ValueError("No Gmail tokens stored. User must connect Gmail first.")

    access_token = gmail_tokens.get("access_token")
    refresh_token = gmail_tokens.get("refresh_token")
    expires_at = gmail_tokens.get("expires_at", 0)

    # Refresh if expired or about to expire (60s buffer)
    if time.time() >= (expires_at - 60):
        if not refresh_token:
            raise ValueError(
                "Access token expired and no refresh token available. "
                "User must re-authorize Gmail."
            )
        refreshed = refresh_access_token(refresh_token)
        gmail_tokens = {
            **gmail_tokens,
            "access_token": refreshed["access_token"],
            "expires_at": refreshed["expires_at"],
        }
        access_token = refreshed["access_token"]
        logger.info("Gmail access token refreshed successfully.")

    return access_token, gmail_tokens


def _get_authenticated_email(access_token: str) -> str:
    """Fetch the email address of the authenticated Google user."""
    with httpx.Client(timeout=10) as client:
        resp = client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code != 200:
            logger.error(f"Failed to fetch user info: {resp.text}")
            return ""
        return resp.json().get("email", "")


def list_send_as_identities(access_token: str) -> List[Dict[str, Any]]:
    """
    List all Send-As identities for the authenticated Gmail account.
    Returns a list of dicts with keys: sendAsEmail, displayName, isDefault,
    isPrimary, verificationStatus, etc.
    """
    with httpx.Client(timeout=10) as client:
        resp = client.get(
            f"{GMAIL_API_BASE}/users/me/settings/sendAs",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code != 200:
            logger.error(f"Failed to list Send-As identities: {resp.status_code} {resp.text}")
            raise ValueError(f"Failed to fetch Send-As identities: {resp.text}")
        data = resp.json()

    return data.get("sendAs", [])


def validate_send_as_identity(
    access_token: str, sender_email: str
) -> Dict[str, Any]:
    """
    Validate that sender_email is a verified Send-As identity on the
    connected Gmail account. Returns the Send-As identity dict if valid.
    Raises ValueError if not found or not verified.
    """
    identities = list_send_as_identities(access_token)
    sender_lower = sender_email.strip().lower()

    for identity in identities:
        identity_email = (identity.get("sendAsEmail") or "").strip().lower()
        if identity_email == sender_lower:
            # Primary account is always verified
            if identity.get("isPrimary", False):
                return identity
            # Non-primary must have accepted verification
            status = identity.get("verificationStatus", "")
            if status == "accepted":
                return identity
            else:
                raise ValueError(
                    f"Send-As identity '{sender_email}' exists but is not verified "
                    f"(status: '{status}'). Please verify it in Gmail Settings → "
                    f"Accounts → Send mail as."
                )

    available = [i.get("sendAsEmail") for i in identities]
    raise ValueError(
        f"'{sender_email}' is not a configured Send-As identity on the connected "
        f"Gmail account. Available Send-As addresses: {available}. "
        f"Add and verify '{sender_email}' in Gmail Settings → Accounts → Send mail as."
    )


def send_email_via_gmail(
    access_token: str,
    from_email: str,
    from_name: str,
    to_email: str,
    subject: str,
    body: str,
    reply_to: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send an email via Gmail API using a verified Send-As identity.

    1. Validates the from_email is a verified Send-As identity
    2. Constructs an RFC 2822 MIME message
    3. Base64url-encodes it
    4. Sends via POST /gmail/v1/users/me/messages/send

    Returns a dict with the sent message metadata.
    """
    # 1. Validate Send-As identity before sending
    identity = validate_send_as_identity(access_token, from_email)
    verified_email = identity.get("sendAsEmail", from_email)
    display_name = from_name or identity.get("displayName", "")

    # 2. Construct MIME message
    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((display_name, verified_email))
    msg["To"] = to_email.strip()
    msg["Subject"] = subject or "Message from JARVIS CRM"
    if reply_to:
        msg["Reply-To"] = reply_to.strip()

    # Plaintext body
    msg.attach(MIMEText(body or "", "plain", "utf-8"))

    # 3. Base64url encode the message
    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")

    # 4. Send via Gmail API
    with httpx.Client(timeout=15) as client:
        resp = client.post(
            f"{GMAIL_API_BASE}/users/me/messages/send",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={"raw": raw_message},
        )

    if resp.status_code not in (200, 201):
        logger.error(f"Gmail API send failed: {resp.status_code} {resp.text}")
        error_detail = resp.json().get("error", {}).get("message", resp.text)
        raise ValueError(f"Gmail API send failed: {error_detail}")

    result = resp.json()
    logger.info(
        f"Email sent via Gmail API | From: '{display_name}' <{verified_email}> | "
        f"To: <{to_email}> | Subject: '{subject}' | Message ID: {result.get('id')}"
    )

    return {
        "success": True,
        "mode": "GMAIL_API",
        "gmail_message_id": result.get("id"),
        "thread_id": result.get("threadId"),
        "from_email": verified_email,
        "from_name": display_name,
        "to_email": to_email.strip(),
        "subject": subject,
        "message": f"Email sent via Gmail API from {display_name} <{verified_email}> to {to_email}",
    }
