import json
import hashlib
from typing import Optional, Any, Dict, Tuple
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from app.models.idempotency import IdempotencyRecord


def compute_request_hash(data: Any) -> str:
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class IdempotencyService:
    @staticmethod
    def check_and_get(
        db: Session,
        key: Optional[str],
        user_id: str,
        action: str,
        request_payload: Any
    ) -> Optional[Tuple[int, Dict[str, Any]]]:
        """
        If idempotency key exists, returns (cached_status_code, cached_response_body).
        If not found, returns None.
        """
        if not key:
            return None

        record = db.query(IdempotencyRecord).filter(
            IdempotencyRecord.key == key,
            IdempotencyRecord.user_id == user_id
        ).first()

        if record:
            return record.response_status, record.response_body
        return None

    @staticmethod
    def save(
        db: Session,
        key: Optional[str],
        user_id: str,
        action: str,
        request_payload: Any,
        response_status: int,
        response_body: Dict[str, Any]
    ) -> None:
        """
        Saves the processed response for this idempotency key.
        """
        if not key:
            return

        req_hash = compute_request_hash(request_payload)
        record = IdempotencyRecord(
            key=key,
            user_id=user_id,
            action=action,
            request_hash=req_hash,
            response_status=response_status,
            response_body=response_body
        )
        db.add(record)
        try:
            db.commit()
        except Exception:
            db.rollback()


idempotency_service = IdempotencyService()
