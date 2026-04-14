"""Video ingest pipeline.

Flow:
  upload → quarantine → hash → validate → copy to working → probe → persist
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import InsufficientStorage, IngestValidationError, QuarantineHeld
from app.core.integrity import sha256_file
from app.core.video_probe import VideoInfo, probe
from app.db.models import Video, VideoMetadata
from app.services.audit_service import AuditService
from app.services.provenance_service import ProvenanceService


_ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v"}
_MIN_FREE_MB = 500  # refuse ingest if less than 500 MB free


def _ensure_dirs() -> None:
    for p in (
        settings.originals_path,
        settings.working_path,
        settings.quarantine_path,
        settings.thumbnails_path,
        settings.clips_path,
        settings.exports_path,
    ):
        p.mkdir(parents=True, exist_ok=True)


def _check_free_space(path: Path, required_size_bytes: int) -> None:
    stat = shutil.disk_usage(path)
    free_mb = stat.free // (1024 * 1024)
    needed_mb = max(_MIN_FREE_MB, (required_size_bytes * 3) // (1024 * 1024))  # 3× headroom
    if free_mb < needed_mb:
        raise InsufficientStorage(required_mb=needed_mb)


def ingest_file(
    source_path: Path,
    *,
    db: Session,
    source_name: str,
    operator_id: str,
    timezone_str: str = "America/Sao_Paulo",
) -> Video:
    """Ingest a video file into OmniView.

    Returns the persisted Video row (status='scanning' ready for worker).
    """
    _ensure_dirs()

    # Validate extension
    if source_path.suffix.lower() not in _ALLOWED_EXTENSIONS:
        raise IngestValidationError(detail=f"Extension '{source_path.suffix}' not allowed")

    if not source_path.exists():
        raise IngestValidationError(detail=f"File not found: {source_path}")

    file_size = source_path.stat().st_size
    if file_size == 0:
        raise IngestValidationError(detail="File is empty")

    # Check disk space before copying
    _check_free_space(settings.originals_path, file_size)

    # Create Video row (status=uploaded)
    video = Video(
        original_path=str(source_path.resolve()),
        source_name=source_name,
        file_size=file_size,
        ingested_by=operator_id,
        timezone=timezone_str,
        status="hashing",
    )
    db.add(video)
    db.flush()  # get the ID without committing

    audit = AuditService(db)
    audit.log(
        entity_type="video",
        entity_id=video.id,
        action="ingest_started",
        actor_id=operator_id,
        payload={"source": str(source_path), "size_bytes": file_size},
    )

    # Hash original
    sha = sha256_file(source_path)
    video.sha256 = sha

    # Check for duplicate (idempotent ingest by SHA-256)
    existing = db.query(Video).filter(Video.sha256 == sha, Video.id != video.id).first()
    if existing:
        db.delete(video)
        db.commit()
        raise IngestValidationError(
            detail=f"Duplicate video — already ingested as {existing.id}"
        )

    # Copy to originals (read-only)
    dest_name = f"{video.id}{source_path.suffix.lower()}"
    dest_path = settings.originals_path / dest_name
    shutil.copy2(source_path, dest_path)
    dest_path.chmod(0o444)  # read-only

    # Working copy (mutable for processing)
    working_path = settings.working_path / dest_name
    shutil.copy2(dest_path, working_path)

    video.original_path = str(dest_path)
    video.working_copy_path = str(working_path)

    # Probe metadata
    try:
        info: VideoInfo = probe(source_path)
        video.duration_ms = info.duration_ms
        video.fps_nominal = info.fps
        video.width = info.width
        video.height = info.height
        video.status = "scanning"

        meta = VideoMetadata(
            video_id=video.id,
            codec=info.codec,
            bit_rate=info.bit_rate,
            creation_time=info.creation_time,
            container_format=info.container_format,
            extra_json=json.dumps(info.extra),
        )
        db.add(meta)
    except Exception as exc:
        video.status = "failed"
        video.error_code = "OMNI-003"
        video.error_detail = str(exc)[:512]
        db.commit()
        raise

    # Write provenance JSON
    ProvenanceService.write_initial(video)

    audit.log(
        entity_type="video",
        entity_id=video.id,
        action="ingest_completed",
        actor_id=operator_id,
        payload={
            "sha256": sha,
            "duration_ms": video.duration_ms,
            "dest": str(dest_path),
        },
    )

    db.commit()
    return video
