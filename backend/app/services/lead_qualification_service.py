"""Canonical lead-segment classification and filtering rules.

``segment`` answers *who the lead represents* (B2B, B2C, or OTHER).  It is
not a substitute for ``lead_type`` (for example, INBOUND or OUTBOUND).
"""
from typing import Optional


BUSINESS_SEGMENTS = {"B2B", "B2C"}
VALID_SEGMENTS = BUSINESS_SEGMENTS | {"OTHER"}

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "rediffmail.com",
    "icloud.com", "live.com", "msn.com", "aol.com",
}


def normalize_segment(value: Optional[str]) -> Optional[str]:
    """Normalize an explicitly supplied segment without silently guessing it."""
    if value is None or not str(value).strip():
        return None
    normalized = str(value).strip().upper()
    if normalized not in VALID_SEGMENTS:
        raise ValueError("segment must be one of B2B, B2C, or OTHER")
    return normalized


def classify_segment(company_name: Optional[str], email: Optional[str]) -> str:
    """Classify only when available source data supports the result.

    A company name alone is not enough to call a lead B2B, and a missing email
    is not enough to call a lead B2C.  Such records remain OTHER and can be
    reviewed instead of being incorrectly qualified.
    """
    company_present = bool(company_name and company_name.strip())
    normalized_email = (email or "").strip().lower()
    if normalized_email and "@" in normalized_email:
        domain = normalized_email.rsplit("@", 1)[1]
        if domain in FREE_EMAIL_DOMAINS:
            return "B2C"
        if company_present:
            return "B2B"
    return "OTHER"


def resolve_segment(
    explicit_segment: Optional[str], company_name: Optional[str], email: Optional[str]
) -> str:
    return normalize_segment(explicit_segment) or classify_segment(company_name, email)
