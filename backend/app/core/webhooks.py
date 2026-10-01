"""Shared verification for unauthenticated provider webhook endpoints."""
import hashlib
import hmac

from fastapi import HTTPException, Request, status


async def verify_hmac_webhook(request: Request, secret: str | None, header_name: str) -> None:
    """Require a hex HMAC-SHA256 over the exact request body.

    Rejecting an unconfigured integration is intentional: accepting an unsigned
    callback is worse than a temporarily unavailable integration.
    """
    if not secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Webhook integration is not configured")
    signature = request.headers.get(header_name)
    if not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing webhook signature")
    expected = hmac.new(secret.encode("utf-8"), await request.body(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")
