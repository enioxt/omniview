"""PII Gate — Guard Brasil wrapper for LGPD compliance.

Scans filenames and metadata before they are persisted in the database.
If Guard Brasil API is unreachable (offline/local-only deployment), logs a
warning and allows ingest to continue — OmniView must work without cloud.

Usage:
    from app.core.pii_gate import pii_scan_name

    safe_name = pii_scan_name("CPF 123.456.789-09.mp4")
    # Returns masked name if PII found; original if safe; original on API error.
"""
from __future__ import annotations

import os

import structlog

log = structlog.get_logger(__name__)

# Guard Brasil is optional — graceful degradation if unavailable
try:
    from guard_brasil import GuardBrasil

    _guard = GuardBrasil(
        api_key=os.getenv("GUARD_BRASIL_API_KEY", ""),
        timeout=5.0,
    )
    _GUARD_AVAILABLE = True
except Exception:  # noqa: BLE001
    _guard = None  # type: ignore[assignment]
    _GUARD_AVAILABLE = False


def pii_scan_name(original: str) -> str:
    """Scan a filename/source name for Brazilian PII.

    Returns the masked string if PII is found.
    Returns original unchanged if Guard Brasil is unavailable (graceful degradation).
    Always logs a warning when PII is detected so it appears in the audit trail.
    """
    if not _GUARD_AVAILABLE or not original:
        if not _GUARD_AVAILABLE:
            log.debug("pii_gate.unavailable", original=original)
        return original

    try:
        result = _guard.inspect(original)
        if result.has_pii:
            log.warning(
                "pii_gate.pii_detected",
                original_hash=_hash(original),
                pii_found=result.pii_found,
                masked=result.output,
            )
            return result.output
        return original
    except Exception as exc:  # noqa: BLE001
        log.warning("pii_gate.api_error", error=str(exc), original=original)
        return original


def _hash(value: str) -> str:
    import hashlib
    return hashlib.sha256(value.encode()).hexdigest()[:16]
