"""Export routes — /api/videos/{id}/export."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import User
from app.services.export_service import ExportService

router = APIRouter(prefix="/videos", tags=["export"])


@router.post("/{video_id}/export", summary="Export forensic ZIP for a video")
def export_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Build and return a signed forensic ZIP.

    Includes: original, thumbnails, clips, provenance.json, report.html, manifest.json.
    The manifest HMAC can be verified with `omniview-cli verify <zip>`.

    Requires: authenticated user (any role).
    """
    svc = ExportService(db)
    try:
        zip_path = svc.export_video(video_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=zip_path.name,
        headers={"Content-Disposition": f'attachment; filename="{zip_path.name}"'},
    )
