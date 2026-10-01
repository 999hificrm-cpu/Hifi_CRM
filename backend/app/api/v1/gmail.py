"""
Gmail OAuth2 and Send-As API endpoints for JARVIS CRM.

Provides:
  - GET  /gmail/oauth/authorize  — Get Google OAuth consent URL
  - GET  /gmail/oauth/callback   — Handle OAuth callback (stores tokens)
  - GET  /gmail/status           — Check connection status + list Send-As identities
  - POST /gmail/send             — Send email via Gmail API with verified Send-As sender
"""

from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, get_tenant_id
from app.models.user import User
from app.models.lead import Lead
from app.models.activity import Activity
from app.models.audit import RadarEvent
from app.services.gmail_service import (
    is_gmail_configured,
    get_oauth_authorization_url,
    exchange_oauth_code,
    get_valid_access_token,
    list_send_as_identities,
    validate_send_as_identity,
    send_email_via_gmail,
)

router = APIRouter(prefix="/gmail", tags=["Gmail Integration"])


# --- Request/Response Models ---

class GmailSendRequest(BaseModel):
    to_email: str
    from_email: str
    from_name: Optional[str] = None
    subject: str
    body: str
    lead_id: Optional[str] = None
    reply_to: Optional[str] = None


# --- OAuth Endpoints ---

@router.get("/oauth/authorize")
def gmail_oauth_authorize(
    current_user: User = Depends(get_current_user),
):
    """Generate the Google OAuth2 consent URL for the current user."""
    if not is_gmail_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gmail integration is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env"
        )
    url = get_oauth_authorization_url(current_user.id)
    return {"authorization_url": url}


@router.get("/oauth/callback", response_class=HTMLResponse)
def gmail_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Handle the Google OAuth2 callback.
    'state' contains the JARVIS user_id who initiated the flow.
    Stores tokens on the user record and shows a success page.
    """
    user = db.query(User).filter(User.id == state).first()
    if not user:
        return HTMLResponse(
            content="<html><body><h2>Error: User not found.</h2></body></html>",
            status_code=400,
        )

    try:
        tokens = exchange_oauth_code(code)
    except Exception as e:
        return HTMLResponse(
            content=f"<html><body><h2>OAuth Error</h2><p>{str(e)}</p></body></html>",
            status_code=400,
        )

    # Store tokens on the user record
    user.gmail_tokens = tokens
    db.commit()

    return HTMLResponse(content=f"""
    <html>
    <head><title>Gmail Connected — JARVIS CRM</title></head>
    <body style="font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; background: #0f172a; color: white;">
      <div style="text-align: center; max-width: 480px; padding: 40px; background: #1e293b; border-radius: 16px; border: 1px solid #334155;">
        <div style="font-size: 3rem; margin-bottom: 16px;">✅</div>
        <h1 style="font-size: 1.5rem; margin-bottom: 8px;">Gmail Connected Successfully</h1>
        <p style="color: #94a3b8; margin-bottom: 16px;">
          Connected as <strong style="color: #60a5fa;">{tokens.get('email', 'unknown')}</strong>
        </p>
        <p style="color: #64748b; font-size: 0.875rem;">
          You can close this window and return to JARVIS CRM.
          Your Send-As identities are now available for email dispatch.
        </p>
        <script>
          setTimeout(function() {{ if (window.opener) {{ window.opener.postMessage('gmail_connected', '*'); window.close(); }} }}, 2000);
        </script>
      </div>
    </body>
    </html>
    """)


# --- Status / Send-As Endpoints ---

@router.get("/status")
def gmail_status(
    current_user: User = Depends(get_current_user),
):
    """
    Check Gmail connection status and list verified Send-As identities.
    """
    if not is_gmail_configured():
        return {
            "configured": False,
            "connected": False,
            "message": "Gmail integration not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        }

    if not current_user.gmail_tokens:
        return {
            "configured": True,
            "connected": False,
            "google_account": None,
            "send_as_identities": [],
            "message": "Gmail not connected. Please authorize via OAuth.",
        }

    try:
        access_token, updated_tokens = get_valid_access_token(current_user.gmail_tokens)
    except ValueError as e:
        return {
            "configured": True,
            "connected": False,
            "error": str(e),
            "message": "Gmail tokens expired or invalid. Please re-authorize.",
        }

    # Persist refreshed tokens if they changed
    if updated_tokens != current_user.gmail_tokens:
        # We can't commit here without db session — return the info and let
        # the caller decide. But for GET endpoints, we'll skip token persistence
        # and rely on send-time refresh.
        pass

    try:
        identities = list_send_as_identities(access_token)
    except ValueError:
        identities = []

    verified = [
        {
            "email": i.get("sendAsEmail"),
            "display_name": i.get("displayName", ""),
            "is_primary": i.get("isPrimary", False),
            "is_default": i.get("isDefault", False),
            "verification_status": i.get("verificationStatus", ""),
        }
        for i in identities
        if i.get("isPrimary") or i.get("verificationStatus") == "accepted"
    ]

    return {
        "configured": True,
        "connected": True,
        "google_account": current_user.gmail_tokens.get("email"),
        "send_as_identities": verified,
        "message": f"Gmail connected. {len(verified)} verified Send-As identit{'y' if len(verified) == 1 else 'ies'} available.",
    }


# --- Send Endpoint ---

@router.post("/send")
def gmail_send(
    payload: GmailSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Send an email via Gmail API using a verified Send-As identity.
    Validates the from_email is a verified Send-As alias before sending.
    """
    if not is_gmail_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gmail integration not configured.",
        )

    if not current_user.gmail_tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected. Please connect your Gmail account first.",
        )

    # Get valid access token (refreshing if needed)
    try:
        access_token, updated_tokens = get_valid_access_token(current_user.gmail_tokens)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    # Persist refreshed tokens
    if updated_tokens != current_user.gmail_tokens:
        current_user.gmail_tokens = updated_tokens
        db.commit()

    # Validate recipient
    to_email = (payload.to_email or "").strip()
    if not to_email or "@" not in to_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid recipient email address is required.",
        )

    # Validate and send
    from_name = payload.from_name or current_user.full_name or "JARVIS CRM"
    reply_to = payload.reply_to or current_user.email

    try:
        result = send_email_via_gmail(
            access_token=access_token,
            from_email=payload.from_email,
            from_name=from_name,
            to_email=to_email,
            subject=payload.subject,
            body=payload.body,
            reply_to=reply_to,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Log activity if lead_id provided
    if payload.lead_id:
        lead = db.query(Lead).filter(
            Lead.id == payload.lead_id,
            Lead.organization_id == tenant_id,
        ).first()
        if lead:
            activity = Activity(
                organization_id=tenant_id,
                lead_id=lead.id,
                company_id=lead.company_id,
                contact_id=lead.contact_id,
                user_id=current_user.id,
                activity_type="EMAIL",
                subject=payload.subject or "Email Sent via Gmail",
                description=(
                    f"Sent via Gmail API (Send-As)\n\n"
                    f"From: {result['from_name']} <{result['from_email']}>\n"
                    f"To: {result['to_email']}\n"
                    f"Reply-To: {reply_to}\n\n"
                    f"{payload.body}"
                ),
                status="COMPLETED",
            )
            db.add(activity)

            radar_event = RadarEvent(
                organization_id=tenant_id,
                actor_user_id=current_user.id,
                action="GMAIL_EMAIL_SENT",
                entity_type="LEAD",
                entity_id=lead.id,
            )
            db.add(radar_event)
            db.commit()

    return {
        "status": "success",
        "message": result["message"],
        "result": result,
    }
