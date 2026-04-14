"""Integration tests for export route and export_service.export_video()."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.auth import hash_password
from app.db.base import Base
from app.db.models import Event, User, Video
from app.main import create_app
from app.services.export_service import ExportService

# ── Shared in-memory DB ───────────────────────────────────────────────────────

_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(_ENGINE)
_Session = sessionmaker(bind=_ENGINE, autocommit=False, autoflush=False)

with _Session() as _db:
    _db.add(User(
        username="exporttest",
        hashed_password=hash_password("pass"),
        role="admin",
    ))
    _db.commit()


def override_db():  # type: ignore[return]
    db = _Session()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client() -> TestClient:  # type: ignore[return]
    app = create_app()
    app.dependency_overrides[get_db] = override_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c  # type: ignore[misc]


def _login(client: TestClient) -> None:
    client.post("/api/auth/login", json={"username": "exporttest", "password": "pass"})


# ── Export API ────────────────────────────────────────────────────────────────

def test_export_video_not_found(client: TestClient) -> None:
    _login(client)
    r = client.post("/api/videos/nonexistent-id/export")
    assert r.status_code == 404


def test_export_video_not_completed(client: TestClient) -> None:
    """Video in 'scanning' status should return 404."""
    _login(client)
    with _Session() as db:
        v = Video(
            original_path="/tmp/test.mp4",
            source_name="cam_export_test",
            status="scanning",
            ingested_by="test",
        )
        db.add(v)
        db.commit()
        vid_id = v.id

    r = client.post(f"/api/videos/{vid_id}/export")
    assert r.status_code == 404
    assert "not completed" in r.json()["detail"]


def test_export_unauthenticated() -> None:
    app = create_app()
    app.dependency_overrides[get_db] = override_db
    with TestClient(app, raise_server_exceptions=False) as fresh:
        r = fresh.post("/api/videos/someid/export")
    assert r.status_code == 401


# ── ExportService.export_video() ──────────────────────────────────────────────

def test_export_service_creates_valid_zip(tmp_path: Path) -> None:
    """export_video() should create a valid ZIP with manifest + HMAC."""
    db = MagicMock()

    # Build a minimal completed Video mock
    video = MagicMock(spec=Video)
    video.id = "test-video-123"
    video.status = "completed"
    video.source_name = "cam_test"
    video.original_path = str(tmp_path / "orig.mp4")
    video.working_copy_path = None
    video.sha256 = "abc" * 21 + "ab"
    video.duration_ms = 60000
    video.fps_nominal = 25.0
    video.width = 1920
    video.height = 1080
    video.ingested_at = __import__("datetime").datetime.now()

    # Create a fake original file
    Path(video.original_path).write_bytes(b"fake video")

    db.get.return_value = video
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []  # no events
    db.query.return_value.filter.return_value.all.return_value = []

    with (
        patch("app.services.export_service.settings") as mock_settings,
        patch("app.services.export_service.ProvenanceService.read", return_value={}),
    ):
        mock_settings.exports_path = tmp_path / "exports"
        mock_settings.secret_key = "test-secret"
        mock_settings.storage_path = tmp_path

        svc = ExportService(db)
        zip_path = svc.export_video("test-video-123")

    assert zip_path.exists()
    assert zip_path.suffix == ".zip"

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        assert "provenance.json" in names
        assert "report.html" in names

        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["video_id"] == "test-video-123"
        assert "hmac" in manifest
        assert len(manifest["hmac"]) == 64

    # The file we just created should verify
    with patch("app.services.export_service.settings") as ms2:
        ms2.secret_key = "test-secret"
        result = ExportService.verify_zip(zip_path)
    assert result is True


def test_export_service_missing_original_still_creates_zip(tmp_path: Path) -> None:
    """Missing original file should not crash — ZIP is still created."""
    db = MagicMock()

    video = MagicMock(spec=Video)
    video.id = "vid-no-orig"
    video.status = "completed"
    video.source_name = "cam"
    video.original_path = str(tmp_path / "missing.mp4")  # does not exist
    video.working_copy_path = None
    video.sha256 = None
    video.duration_ms = None
    video.fps_nominal = None
    video.width = None
    video.height = None
    video.ingested_at = __import__("datetime").datetime.now()

    db.get.return_value = video
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.filter.return_value.all.return_value = []

    with (
        patch("app.services.export_service.settings") as mock_settings,
        patch("app.services.export_service.ProvenanceService.read", return_value={}),
    ):
        mock_settings.exports_path = tmp_path / "exports2"
        mock_settings.secret_key = "test-secret"
        mock_settings.storage_path = tmp_path

        svc = ExportService(db)
        zip_path = svc.export_video("vid-no-orig")

    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        assert "manifest.json" in zf.namelist()
