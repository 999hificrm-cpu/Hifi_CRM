from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models.masking import MaskingPolicy, MaskingException
from app.models.user import User


def mask_phone_number(phone: str) -> str:
    if not phone or len(phone) < 6:
        return "******"
    clean_phone = phone.strip()
    # Keep first 4 and last 2 or 3 digits
    prefix = clean_phone[:4]
    suffix = clean_phone[-3:]
    return f"{prefix}****{suffix}"


def mask_email_address(email: str) -> str:
    if not email or "@" not in email:
        return "****@***.com"
    parts = email.strip().split("@")
    user_part = parts[0]
    domain_part = parts[1]
    if len(user_part) <= 2:
        masked_user = user_part[0] + "***"
    else:
        masked_user = user_part[:2] + "****" + user_part[-1]
    return f"{masked_user}@{domain_part}"


def should_mask_field(
    db: Session,
    organization_id: str,
    user: User,
    field: str,
    lead_id: str = None
) -> bool:
    """
    Determines if a field should be masked for the given user.
    - Super admins and Org Admins/Managers NEVER have masked fields.
    - Roles like TELECALLER are checked against MaskingPolicy.
    - Active MaskingException overrides policy.
    """
    if user.is_super_admin or user.tenant_role in ("ORG_ADMIN", "SALES_MANAGER"):
        return False

    # Check for temporary active exception
    if lead_id:
        now = datetime.now(timezone.utc)
        exception = db.query(MaskingException).filter(
            MaskingException.organization_id == organization_id,
            MaskingException.lead_id == lead_id,
            MaskingException.user_id == user.id,
            MaskingException.field == field,
            MaskingException.expires_at > now
        ).first()
        if exception:
            return False

    # Check masking policy for user's role
    role = user.tenant_role or "TELECALLER"
    policy = db.query(MaskingPolicy).filter(
        MaskingPolicy.organization_id == organization_id,
        MaskingPolicy.tenant_role == role,
        MaskingPolicy.field == field
    ).first()

    if policy:
        return policy.is_masked
    # Default to masking for telecallers
    return role == "TELECALLER"
