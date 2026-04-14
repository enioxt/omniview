"""Video management endpoints — upload, list, detail, provenance, delete."""
from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import AdminUser, CurrentUser, get_db
from app.api.schemas import VideoResponse
from app.core.ingest import ingest_file
from app.db.models import Event, Video
from app.services.provenance_service import ProvenanceService
from app.workers.scan_worker import process_video_async

router = APIRouter(prefix="/videos", tags=["videos"])


def _to_response(video: Video, db: Session) -> VideoResponse:
    event_count = db.query(Event).filter(Event.video_id == video.id).count()
    return VideoResponse(
        id=video.id,
        status=video.status,
        sha256=video.sha256,
        source_name=video.source_name,
        duration_ms=video.duration_ms,
        fps_nominal=video.fps_nominal,
        width=video.width,
        height=video.height,
        ingested_at=video.ingested_at,
        event_count=event_count,
    )


@router.post("", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    source_name: str = Form(...),
    timezone: str = Form("America/Sao_Paulo"),
) -> VideoResponse:
    """Upload a video file, ingest it, and queue a background scan."""
    # Write upload to a temp file then call synchronous ingest_file
    suffix = Path(file.filename or "upload").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        video = ingest_file(
            tmp_path,
            db=db,
            source_name=source_name,
            operator_id=current_user.id,
            timezone_str=timezone,
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    # Fire-and-forget scan in background
    asyncio.create_task(process_video_async(video, db))

    return _to_response(video, db)


@router.get("", response_model=list[VideoResponse])
def list_videos(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 50,
) -> list[VideoResponse]:
    videos = db.query(Video).order_by(Video.ingested_at.desc()).offset(skip).limit(limit).all()
    return [_to_response(v, db) for v in videos]


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(
    video_id: str,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> VideoResponse:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return _to_response(video, db)


@router.get("/{video_id}/provenance")
def get_provenance(
    video_id: str,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return ProvenanceService.read(video_id)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    video_id: str,
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Permanently delete video and all associated files. Admin only."""
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    for path_str in [video.original_path, video.working_copy_path]:
        if path_str:
            p = Path(path_str)
            p.unlink(missing_ok=True)

    db.delete(video)
    db.commit()
