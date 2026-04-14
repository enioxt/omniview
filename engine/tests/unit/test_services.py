"""Unit tests for audit_service and provenance_service."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── AuditService ──────────────────────────────────────────────────────────────

class TestAuditService:
    def _make_db(self):
        db = MagicMock()
        db.add = MagicMock()
        return db

    def test_log_creates_audit_row(self):
        from app.services.audit_service import AuditService
        db = self._make_db()
        svc = AuditService(db)
        row = svc.log(entity_type="video", action="test_action", actor_id="user1")
        db.add.assert_called_once()
        assert row.entity_type == "video"
        assert row.action == "test_action"
        assert row.row_hmac  # non-empty HMAC

    def test_log_result_field_stored_in_payload(self):
        from app.services.audit_service import AuditService
        db = self._make_db()
        svc = AuditService(db)
        row = svc.log(
            entity_type="user",
            action="login",
            result="denied",
            reasoning="bad password",
        )
        payload = json.loads(row.payload_json)
        assert payload["__result"] == "denied"
        assert payload["__reasoning"] == "bad password"

    def test_verify_row_valid(self):
        from app.services.audit_service import AuditService
        db = self._make_db()
        svc = AuditService(db)
        row = svc.log(
            entity_type="event",
            entity_id="ev1",
            action="review_submitted",
            actor_id="reviewer1",
            payload={"label": "person"},
        )
        assert AuditService.verify_row(row) is True

    def test_verify_row_tampered_hmac(self):
        from app.services.audit_service import AuditService
        db = self._make_db()
        svc = AuditService(db)
        row = svc.log(entity_type="video", action="ingest_started")
        row.row_hmac = "0" * 64  # tampered
        assert AuditService.verify_row(row) is False

    def test_verify_row_tampered_action(self):
        from app.services.audit_service import AuditService
        db = self._make_db()
        svc = AuditService(db)
        row = svc.log(entity_type="video", action="ingest_started")
        row.action = "deleted_video"  # tampered
        assert AuditService.verify_row(row) is False

    def test_log_defaults(self):
        from app.services.audit_service import AuditService
        db = self._make_db()
        row = AuditService(db).log(entity_type="x", action="y")
        payload = json.loads(row.payload_json)
        assert payload["__result"] == "allowed"
        assert payload["__reasoning"] == ""


# ── ProvenanceService ─────────────────────────────────────────────────────────

class TestProvenanceService:
    def _make_video(self, vid_id: str) -> MagicMock:
        from datetime import datetime, timezone
        video = MagicMock()
        video.id = vid_id
        video.source_name = "cam_test"
        video.sha256 = "abc123"
        video.original_path = "/tmp/test.mp4"
        video.working_copy_path = None
        video.ingested_by = "tester"
        video.timezone = "America/Sao_Paulo"
        video.ingested_at = datetime.now(timezone.utc)
        return video

    def test_write_initial(self, tmp_path: Path):
        from app.services.provenance_service import ProvenanceService

        video = self._make_video("prov-test-1")
        with patch("app.services.provenance_service.settings") as ms:
            ms.working_path = tmp_path
            ProvenanceService.write_initial(video)
            prov_file = tmp_path / "provenance" / "prov-test-1_provenance.json"
            assert prov_file.exists()
            data = json.loads(prov_file.read_text())
            assert data["video_id"] == "prov-test-1"
            assert data["original_sha256"] == "abc123"
            assert "transforms" in data

    def test_append_transform(self, tmp_path: Path):
        from app.services.provenance_service import ProvenanceService

        video = self._make_video("prov-test-2")
        with patch("app.services.provenance_service.settings") as ms:
            ms.working_path = tmp_path
            ProvenanceService.write_initial(video)
            ProvenanceService.append_transform(
                "prov-test-2",
                "motion_scan",
                {"frames_with_motion": 42},
            )
            prov_file = tmp_path / "provenance" / "prov-test-2_provenance.json"
            data = json.loads(prov_file.read_text())
            assert len(data["transforms"]) == 1
            assert data["transforms"][0]["type"] == "motion_scan"
            assert data["transforms"][0]["frames_with_motion"] == 42

    def test_read_returns_empty_for_missing(self, tmp_path: Path):
        from app.services.provenance_service import ProvenanceService
        with patch("app.services.provenance_service.settings") as ms:
            ms.working_path = tmp_path
            result = ProvenanceService.read("no-such-id")
        assert result == {}


# ── scan_worker helpers ───────────────────────────────────────────────────────

class TestScanWorkerHelpers:
    def test_cfg_dict_none(self):
        from app.workers.scan_worker import _cfg_dict
        assert _cfg_dict(None) == {}

    def test_cfg_dict_with_config(self):
        from app.core.motion import MotionConfig
        from app.workers.scan_worker import _cfg_dict
        cfg = MotionConfig(score_threshold=30.0, min_area=600, sample_every=5)
        d = _cfg_dict(cfg)
        assert d["score_threshold"] == 30.0
        assert d["min_area"] == 600
        assert d["sample_every"] == 5

    def test_fail_sets_video_status(self):
        from app.workers.scan_worker import _fail
        video = MagicMock()
        db = MagicMock()
        _fail(video, db, "OMNI-100", "test error" * 200)  # long detail — truncated to 512
        assert video.status == "failed"
        assert video.error_code == "OMNI-100"
        assert len(video.error_detail) <= 512
        db.commit.assert_called_once()


# ── progress module ───────────────────────────────────────────────────────────

class TestProgress:
    def test_update_and_subscribe(self):
        import asyncio
        from app.core import progress as prog

        prog.cleanup("test-video-progress")
        q = prog.subscribe("test-video-progress")
        prog.update("test-video-progress", 50, "scanning")

        msg = asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(q.get(), timeout=1.0)
        )
        assert msg["type"] == "progress"
        assert msg["pct"] == 50

    def test_complete_sends_done(self):
        import asyncio
        from app.core import progress as prog

        prog.cleanup("test-video-done")
        q = prog.subscribe("test-video-done")
        prog.complete("test-video-done", event_count=7)

        msg = asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(q.get(), timeout=1.0)
        )
        assert msg["type"] == "done"
        assert msg["event_count"] == 7

    def test_fail_sends_error(self):
        import asyncio
        from app.core import progress as prog

        prog.cleanup("test-video-fail")
        q = prog.subscribe("test-video-fail")
        prog.fail("test-video-fail", "some error")

        msg = asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(q.get(), timeout=1.0)
        )
        assert msg["type"] == "error"
        assert msg["message"] == "some error"

    def test_subscribe_after_done_gets_terminal_immediately(self):
        import asyncio
        from app.core import progress as prog

        prog.cleanup("test-video-late")
        prog.complete("test-video-late", event_count=3)
        q = prog.subscribe("test-video-late")  # subscribe AFTER done

        msg = asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(q.get(), timeout=1.0)
        )
        assert msg["type"] == "done"
