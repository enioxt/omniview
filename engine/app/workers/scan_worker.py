"""Scan worker — processes a video through the full motion pipeline.

Orchestrates: motion scan → event grouping → thumbnails → clips → DB persist.
Called by the API after ingest, or by the CLI.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable

from sqlalchemy.orm import Session

from app.core.clips import extract_clip
from app.core.config import settings
from app.core.event_grouping import MotionEvent, group_motion_frames
from app.core.motion import MotionConfig, scan_video
from app.core.thumbnails import extract_thumbnail
from app.db.models import Event, EventAsset, Video
from app.services.audit_service import AuditService
from app.services.provenance_service import ProvenanceService


def process_video(
    video: Video,
    db: Session,
    motion_config: MotionConfig | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
) -> list[Event]:
    """Run the full motion pipeline on an ingested video.

    Updates video.status throughout. Returns persisted Event rows.
    """
    video.status = "processing"
    db.commit()

    audit = AuditService(db)
    working_path = Path(video.working_copy_path or video.original_path)

    # ── 1. Scan for motion frames ───────────────────────────────────────────
    try:
        motion_frames = list(
            scan_video(working_path, config=motion_config, progress_callback=progress_cb)
        )
    except Exception as exc:
        _fail(video, db, "OMNI-100", str(exc))
        raise

    ProvenanceService.append_transform(
        video.id,
        "motion_scan",
        {"frames_with_motion": len(motion_frames), "config": _cfg_dict(motion_config)},
    )

    # ── 2. Group into events ────────────────────────────────────────────────
    events_raw: list[MotionEvent] = group_motion_frames(motion_frames)

    ProvenanceService.append_transform(
        video.id,
        "event_grouping",
        {"events_found": len(events_raw)},
    )

    # ── 3. Persist events + assets ──────────────────────────────────────────
    db_events: list[Event] = []

    for idx, me in enumerate(events_raw):
        event = Event(
            video_id=video.id,
            event_index=idx,
            start_pts_ms=me.start_pts_ms,
            end_pts_ms=me.end_pts_ms,
            start_frame=me.start_frame,
            end_frame=me.end_frame,
            peak_motion_score=me.peak_motion_score,
            peak_frame=me.peak_frame,
            total_motion_area=me.total_motion_area,
            detection_mode="motion_only",
        )
        db.add(event)
        db.flush()  # get event.id

        # Thumbnail
        thumb_path = settings.thumbnails_path / video.id / f"{event.id}.webp"
        try:
            thumb_sha = extract_thumbnail(working_path, me.peak_frame, thumb_path)
            db.add(EventAsset(
                event_id=event.id,
                asset_type="thumbnail_webp",
                path=str(thumb_path),
                sha256=thumb_sha,
            ))
        except Exception:
            pass  # thumbnail failure is non-fatal

        # Short clip (optional)
        if settings.clip_enabled:
            clip_path = settings.clips_path / video.id / f"{event.id}.mp4"
            try:
                clip_sha = extract_clip(
                    working_path, me.start_pts_ms, me.end_pts_ms, clip_path
                )
                db.add(EventAsset(
                    event_id=event.id,
                    asset_type="clip_mp4",
                    path=str(clip_path),
                    sha256=clip_sha,
                ))
            except Exception:
                pass  # clip failure is non-fatal

        db_events.append(event)

    # ── 4. Mark completed ───────────────────────────────────────────────────
    video.status = "completed"
    db.commit()

    ProvenanceService.append_transform(
        video.id,
        "scan_completed",
        {"total_events": len(db_events)},
    )

    audit.log(
        entity_type="video",
        entity_id=video.id,
        action="scan_completed",
        payload={"events": len(db_events)},
    )
    db.commit()

    return db_events


async def process_video_async(
    video: Video,
    db: Session,
    motion_config: MotionConfig | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
) -> list[Event]:
    """Async wrapper — runs CPU-bound work in thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, process_video, video, db, motion_config, progress_cb
    )


def _fail(video: Video, db: Session, code: str, detail: str) -> None:
    video.status = "failed"
    video.error_code = code
    video.error_detail = detail[:512]
    db.commit()


def _cfg_dict(cfg: MotionConfig | None) -> dict[str, object]:
    if cfg is None:
        return {}
    return {
        "score_threshold": cfg.score_threshold,
        "min_area": cfg.min_area,
        "sample_every": cfg.sample_every,
    }
