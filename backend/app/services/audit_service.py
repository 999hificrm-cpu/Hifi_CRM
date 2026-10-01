import json
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.audit import AuditLog
from app.models.user import User

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


class CentralizedAuditService:
    """
    Centralized, immutable audit service with SHA-256 cryptographic hash chaining
    (Problems #22, #23, #24, #46).
    """

    @classmethod
    def _format_timestamp(cls, ts: Optional[datetime], db: Optional[Session] = None) -> str:
        if not ts:
            return ""
        if ts.tzinfo is not None:
            return ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        if db is not None:
            try:
                dialect_name = db.bind.dialect.name if db.bind else ""
                if dialect_name == "postgresql":
                    return ts.astimezone().astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
        return ts.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _compute_hash(
        previous_hash: str,
        actor_id: Optional[str],
        action: str,
        entity_type: str,
        entity_id: Optional[str],
        timestamp_str: str,
        new_values: Optional[Dict[str, Any]]
    ) -> str:
        payload_str = json.dumps(new_values, sort_keys=True, default=str) if new_values else ""
        raw = f"{previous_hash}|{actor_id or 'SYSTEM'}|{action}|{entity_type}|{entity_id or ''}|{timestamp_str}|{payload_str}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


    @classmethod
    def record(
        cls,
        db: Session,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        actor: Optional[User] = None,
        actor_user_id: Optional[str] = None,
        target_user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: Optional[str] = None,
        support_session_id: Optional[str] = None,
        context_type: Optional[str] = None,
    ) -> AuditLog:
        """
        Records an immutable audit event into the centralized log with SHA-256 hash chaining.
        """
        # Resolve actor ID
        resolved_actor_id = actor_user_id or (actor.id if actor else None)
        resolved_org_id = organization_id or (actor.organization_id if actor else None)

        # Resolve context
        if not context_type:
            if support_session_id:
                context_type = "SUPPORT_CONTEXT"
            elif resolved_org_id:
                context_type = "TENANT_CONTEXT"
            else:
                context_type = "PLATFORM_CONTEXT"

        now = datetime.now(timezone.utc)
        now_str = cls._format_timestamp(now)

        # Find the latest audit event to form cryptographic link
        latest_entry = db.query(AuditLog.event_hash, AuditLog.sequence_number).filter(
            AuditLog.event_hash.isnot(None)
        ).order_by(desc(AuditLog.sequence_number), desc(AuditLog.created_at)).first()

        prev_hash = latest_entry[0] if latest_entry and latest_entry[0] else GENESIS_HASH
        next_seq = (latest_entry[1] + 1) if latest_entry and latest_entry[1] else 1

        # Compute tamper-evident hash
        current_hash = cls._compute_hash(
            previous_hash=prev_hash,
            actor_id=resolved_actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            timestamp_str=now_str,
            new_values=new_values
        )

        entry = AuditLog(
            organization_id=resolved_org_id,
            user_id=resolved_actor_id,
            actor_user_id=resolved_actor_id,
            target_user_id=target_user_id,
            support_session_id=support_session_id,
            context_type=context_type,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            reason=reason,
            sequence_number=next_seq,
            previous_event_hash=prev_hash,
            event_hash=current_hash,
            created_at=now
        )

        db.add(entry)
        try:
            db.commit()
            db.refresh(entry)
        except Exception:
            db.rollback()
            raise

        return entry

    @classmethod
    def verify_chain(cls, db: Session, limit: int = 500) -> Dict[str, Any]:
        """
        Verifies the cryptographic integrity of the audit log sequence.
        Returns whether the chain is fully verified or has been tampered with.
        """
        logs = db.query(AuditLog).filter(
            AuditLog.event_hash.isnot(None)
        ).order_by(AuditLog.sequence_number.asc()).limit(limit).all()
        if not logs:
            return {"status": "VALID", "verified_count": 0, "message": "No audit records to verify"}

        expected_prev = logs[0].previous_event_hash or GENESIS_HASH
        for idx, entry in enumerate(logs):
            if entry.previous_event_hash and entry.previous_event_hash != expected_prev and idx > 0:
                return {
                    "status": "TAMPERED",
                    "verified_count": idx,
                    "tampered_at_id": entry.id,
                    "index": idx,
                    "message": f"Mismatched previous_event_hash at record {entry.id}. Expected {expected_prev}, got {entry.previous_event_hash}"
                }



            expected_curr = cls._compute_hash(
                previous_hash=entry.previous_event_hash or expected_prev,
                actor_id=entry.actor_user_id or entry.user_id,
                action=entry.action,
                entity_type=entry.entity_type,
                entity_id=entry.entity_id,
                timestamp_str=cls._format_timestamp(entry.created_at, db=db),
                new_values=entry.new_values
            )


            # If the log was created with hash calculation, verify it
            if entry.event_hash and entry.event_hash != expected_curr:
                return {
                    "status": "TAMPERED",
                    "verified_count": idx,
                    "tampered_at_id": entry.id,
                    "index": idx,
                    "message": f"Event hash invalid for record {entry.id}. Calculated: {expected_curr}, Stored: {entry.event_hash}"
                }

            if entry.event_hash:
                expected_prev = entry.event_hash

        return {
            "status": "VALID",
            "verified_count": len(logs),
            "latest_event_hash": expected_prev,
            "message": f"Cryptographic integrity confirmed across {len(logs)} audit records"
        }


audit_service = CentralizedAuditService()
