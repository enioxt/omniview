"""Audit service — append-only tamper-evident log.

Each row gets an HMAC-SHA256 computed over the row content + secret key.
This lets us detect if rows were modified or deleted after the fact.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AuditLog


class AuditService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def log(
        self,
        entity_type: str,
        action: str,
        actor_id: str | None = None,
        entity_id: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> AuditLog:
        payload_json = json.dumps(payload or {}, sort_keys=True)
        entry = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_id=actor_id,
            payload_json=payload_json,
        )
        # Compute HMAC over deterministic content
        content = f"{entry.id}|{entity_type}|{entity_id}|{action}|{actor_id}|{payload_json}"
        entry.row_hmac = hmac.new(
            settings.secret_key.encode(),
            content.encode(),
            hashlib.sha256,
        ).hexdigest()

        self._db.add(entry)
        return entry

    @staticmethod
    def verify_row(row: AuditLog) -> bool:
        """Verify a row's HMAC has not been tampered with."""
        content = (
            f"{row.id}|{row.entity_type}|{row.entity_id}|"
            f"{row.action}|{row.actor_id}|{row.payload_json}"
        )
        expected = hmac.new(
            settings.secret_key.encode(),
            content.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, row.row_hmac or "")
