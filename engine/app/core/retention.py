"""Retention worker — purge videos and their assets past retention policy.

Policy lookup:
  1. RetentionPolicy row matching video.source_name (camera-level policy)
  2. RetentionPolicy row matching "default"
  3. Hard-coded default: 90 days for any, 30 days for non-critical

A video is considered "critical" if any of its events has a review with
priority in ("high", "critical") — these are kept for critical_days.
All others are purged after noncritical_days.

Run via:
    omniview-cli retention --dry-run    # preview
    omniview-cli retention              # execute
Or integrate into a cron/systemd timer.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog
from sqlalchemy.orm import Session

from app.db.models import Event, EventAsset, RetentionPolicy, Review, Video

log = structlog.get_logger(__name__)

_DEFAULT_NONCRITICAL_DAYS = 30
_DEFAULT_CRITICAL_DAYS = 365


def _get_policy(db: Session, source_name: str | None) -> RetentionPolicy | None:
    if source_name:
        policy = db.query(RetentionPolicy).filter(
            RetentionPolicy.camera_or_profile == source_name
        ).first()
        if policy:
            return policy
    return db.query(RetentionPolicy).filter(
        RetentionPolicy.camera_or_profile == "default"
    ).first()


def _is_critical(db: Session, video_id: str) -> bool:
    """True if the video has any reviewed event with high/critical priority."""
    return db.query(Review).join(Event).filter(
        Event.video_id == video_id,
        Review.priority.in_(["high", "critical"]),
    ).count() > 0


def _delete_video_files(video: Video) -> list[str]:
    """Delete all file assets for a video. Returns list of deleted paths."""
    deleted: list[str] = []
    for path_str in [video.original_path, video.working_copy_path]:
        if path_str:
            p = Path(path_str)
            if p.exists():
                p.unlink()
                deleted.append(str(p))

    # Thumbnails and clips are in subdirs named by video.id
    for subdir_name in ("thumbnails", "clips"):
        from app.core.config import settings
        subdir = settings.storage_path / subdir_name / video.id
        if subdir.is_dir():
            shutil.rmtree(subdir)
            deleted.append(str(subdir))

    return deleted


def run_retention(db: Session, dry_run: bool = False) -> dict[str, int]:
    """Scan all completed videos and purge those past their retention window.

    Returns counts: {"checked": N, "purged": N, "skipped": N, "errors": N}
    """
    now = datetime.now(timezone.utc)
    counts = {"checked": 0, "purged": 0, "skipped": 0, "errors": 0}

    videos = db.query(Video).filter(Video.status == "completed").all()
    counts["checked"] = len(videos)

    for video in videos:
        try:
            policy = _get_policy(db, video.source_name)
            if policy:
                noncritical_days = policy.noncritical_days
                critical_days = getattr(policy, "critical_days", _DEFAULT_CRITICAL_DAYS)
            else:
                noncritical_days = _DEFAULT_NONCRITICAL_DAYS
                critical_days = _DEFAULT_CRITICAL_DAYS

            critical = _is_critical(db, video.id)
            retention_days = critical_days if critical else noncritical_days
            cutoff = now - timedelta(days=retention_days)

            ingested_at = video.ingested_at
            if ingested_at.tzinfo is None:
                ingested_at = ingested_at.replace(tzinfo=timezone.utc)

            if ingested_at > cutoff:
                counts["skipped"] += 1
                continue

            log.info(
                "retention.purging",
                video_id=video.id,
                ingested_days_ago=(now - ingested_at).days,
                critical=critical,
                dry_run=dry_run,
            )

            if not dry_run:
                deleted = _delete_video_files(video)
                # Cascade deletes events/assets via DB FK CASCADE
                db.delete(video)
                db.commit()
                log.info("retention.purged", video_id=video.id, files_deleted=len(deleted))

            counts["purged"] += 1

        except Exception as exc:
            log.error("retention.error", video_id=video.id, error=str(exc))
            counts["errors"] += 1

    return counts
