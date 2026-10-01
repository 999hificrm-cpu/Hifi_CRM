"""Organization-local business date helpers.

Timestamps are persisted in UTC.  Anything that represents a business day
(targets, attendance and daily reporting) must be calculated in the tenant's
configured timezone instead of from the host machine's UTC date.
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.models.organization import Organization


def organization_timezone(db: Session, organization_id: str) -> ZoneInfo:
    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    timezone_name = organization.timezone if organization and organization.timezone else "Asia/Kolkata"
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        # A bad tenant setting must not silently move work into the server's
        # local timezone.  The documented application fallback is explicit.
        return ZoneInfo("Asia/Kolkata")


def organization_business_date(db: Session, organization_id: str, now: datetime | None = None):
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(organization_timezone(db, organization_id)).date()


def organization_day_bounds_utc(
    db: Session,
    organization_id: str,
    business_date: date | None = None,
) -> tuple[datetime, datetime]:
    """Return an organization's local business-day bounds as UTC timestamps."""
    tz = organization_timezone(db, organization_id)
    target_date = business_date or organization_business_date(db, organization_id)
    start = datetime.combine(target_date, time.min, tzinfo=tz).astimezone(timezone.utc)
    end = datetime.combine(target_date, time.max, tzinfo=tz).astimezone(timezone.utc)
    return start, end


def followup_preset_due_at(
    db: Session,
    organization_id: str,
    preset: str,
    now: datetime | None = None,
) -> datetime | None:
    """Resolve supported UI presets to a stable organization-local 09:00 due time."""
    normalized = preset.strip().lower()
    if normalized == "none":
        return None
    day_offsets = {"tomorrow": 1, "3days": 3, "nextweek": 7}
    if normalized not in day_offsets:
        raise ValueError("followup_preset must be tomorrow, 3days, nextweek, or none")

    tz = organization_timezone(db, organization_id)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    local_date = current.astimezone(tz).date() + timedelta(days=day_offsets[normalized])
    return datetime.combine(local_date, time(hour=9), tzinfo=tz).astimezone(timezone.utc)
