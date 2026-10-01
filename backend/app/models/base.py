import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, text
from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class SoftDeleteMixin:
    deleted_at = Column(DateTime, nullable=True, index=True)
    deleted_by = Column(String(36), nullable=True)
    deletion_reason = Column(String(500), nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

