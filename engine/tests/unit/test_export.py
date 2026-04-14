"""Unit tests for export_service.py and retention.py."""
from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.export_service import ExportService, _build_manifest, _ms


# ── Manifest helpers ──────────────────────────────────────────────────────────

def test_ms_formatting():
    assert _ms(0) == "00:00:00"
    assert _ms(61000) == "00:01:01"
    assert _ms(3661000) == "01:01:01"


def test_build_manifest_contains_hmac():
    files = [{"path": "a.json", "sha256": "abc", "size": 10}]
    m = _build_manifest("vid123", "2026-01-01T00:00:00+00:00", files)
    assert "hmac" in m
    assert m["video_id"] == "vid123"
    assert len(m["hmac"]) == 64  # SHA-256 hex


def test_manifest_hmac_is_deterministic():
    files = [{"path": "a.json", "sha256": "abc", "size": 10}]
    m1 = _build_manifest("vid", "2026-01-01T00:00:00+00:00", files)
    m2 = _build_manifest("vid", "2026-01-01T00:00:00+00:00", files)
    assert m1["hmac"] == m2["hmac"]


def test_manifest_hmac_changes_with_content():
    files1 = [{"path": "a.json", "sha256": "abc", "size": 10}]
    files2 = [{"path": "a.json", "sha256": "xyz", "size": 10}]
    m1 = _build_manifest("vid", "2026-01-01T00:00:00+00:00", files1)
    m2 = _build_manifest("vid", "2026-01-01T00:00:00+00:00", files2)
    assert m1["hmac"] != m2["hmac"]


# ── verify_zip ────────────────────────────────────────────────────────────────

def test_verify_zip_valid(tmp_path: Path):
    """A ZIP with a valid manifest should pass verification."""
    files = [{"path": "report.html", "sha256": "deadbeef", "size": 100}]
    manifest = _build_manifest("vid123", "2026-01-01T00:00:00+00:00", files)

    zip_path = tmp_path / "test_export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))

    assert ExportService.verify_zip(zip_path) is True


def test_verify_zip_tampered(tmp_path: Path):
    """A ZIP with a modified file entry should fail verification."""
    files = [{"path": "report.html", "sha256": "deadbeef", "size": 100}]
    manifest = _build_manifest("vid123", "2026-01-01T00:00:00+00:00", files)
    # Tamper: change file sha256 after signing
    manifest["files"][0]["sha256"] = "tampered"

    zip_path = tmp_path / "tampered_export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))

    assert ExportService.verify_zip(zip_path) is False


def test_verify_zip_missing_manifest(tmp_path: Path):
    """A ZIP without manifest.json should return False."""
    zip_path = tmp_path / "no_manifest.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("report.html", "<html/>")

    assert ExportService.verify_zip(zip_path) is False


def test_verify_zip_nonexistent(tmp_path: Path):
    """A non-existent file should return False."""
    assert ExportService.verify_zip(tmp_path / "does_not_exist.zip") is False


# ── retention ────────────────────────────────────────────────────────────────

def test_retention_skips_recent_video():
    """Videos ingested recently should not be purged."""
    from app.core.retention import run_retention

    db = MagicMock()
    video = MagicMock()
    video.id = "vid1"
    video.source_name = "cam1"
    video.status = "completed"
    video.ingested_at = datetime.now(timezone.utc)  # just now — should be kept

    db.query.return_value.filter.return_value.all.return_value = [video]
    db.query.return_value.filter.return_value.first.return_value = None  # no policy
    db.query.return_value.join.return_value.filter.return_value.count.return_value = 0

    counts = run_retention(db, dry_run=True)
    assert counts["purged"] == 0
    assert counts["skipped"] == 1


def test_retention_dry_run_does_not_delete():
    """Dry-run should count purges without deleting anything."""
    from datetime import timedelta
    from app.core.retention import run_retention

    db = MagicMock()
    video = MagicMock()
    video.id = "vid2"
    video.source_name = "cam2"
    video.status = "completed"
    # 60 days old — past default 30-day window
    video.ingested_at = datetime.now(timezone.utc) - timedelta(days=60)
    video.original_path = None
    video.working_copy_path = None

    db.query.return_value.filter.return_value.all.return_value = [video]
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.join.return_value.filter.return_value.count.return_value = 0

    counts = run_retention(db, dry_run=True)
    assert counts["purged"] == 1
    # db.delete should NOT have been called in dry_run
    db.delete.assert_not_called()
