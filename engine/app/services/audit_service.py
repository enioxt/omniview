"""Audit service — append-only tamper-evident log.

Each row gets an HMAC-SHA256 computed over the row content + secret key.
This lets us detect if rows were modified or deleted after the fact.

Output schema aligned with @egos/audit AuditEntry (TS kernel package):
  id, timestamp, action, resource (=entity_type/entity_id), result, reasoning, context
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Literal

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
        result: Literal["allowed", "denied"] = "allowed",
        reasoning: str = "",
    ) -> AuditLog:
        """Append an audit entry.

        Args:
            entity_type: Domain type (e.g. "video", "event", "user")
            action: What happened (e.g. "ingest_started", "review_submitted")
            actor_id: User ID who triggered the action
            entity_id: ID of the affected entity
            payload: Arbitrary context (serializable dict)
            result: "allowed" or "denied" — aligns with @egos/audit AuditEntry
            reasoning: Why result was reached (e.g. "admin role satisfied")
        """
        payload_json = json.dumps(payload or {}, sort_keys=True)
        entry = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_id=actor_id,
            payload_json=payload_json,
        )
        # Compute HMAC over deterministic content
        content = (
            f"{entry.id}|{entity_type}|{entity_id}|"
            f"{action}|{actor_id}|{result}|{payload_json}"
        )
        entry.row_hmac = hmac.new(
            settings.secret_key.encode(),
            content.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Store result + reasoning in payload for cross-repo compatibility
        # (@egos/audit uses top-level fields; we encode them in payload_json)
        enriched: dict[str, object] = {
            **(payload or {}),
            "__result": result,
            "__reasoning": reasoning,
        }
        entry.payload_json = json.dumps(enriched, sort_keys=True)

        self._db.add(entry)
        return entry

    @staticmethod
    def verify_row(row: AuditLog) -> bool:
        """Verify a row's HMAC has not been tampered with."""
        raw_payload = json.loads(row.payload_json or "{}")
        # Strip enriched fields to reconstruct original content string
        original_payload: dict[str, object] = {
            k: v for k, v in raw_payload.items() if not k.startswith("__")
        }
        result = raw_payload.get("__result", "allowed")
        payload_json = json.dumps(original_payload, sort_keys=True)

        content = (
            f"{row.id}|{row.entity_type}|{row.entity_id}|"
            f"{row.action}|{row.actor_id}|{result}|{payload_json}"
        )
        expected = hmac.new(
            settings.secret_key.encode(),
            content.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, row.row_hmac or "")
