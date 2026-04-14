"""Event and review endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, ReviewerUser, get_db
from app.api.schemas import EventResponse, ReviewRequest, ReviewResponse
from app.db.models import Event, Review

router = APIRouter(tags=["events"])

_VALID_STATUSES = {"pending_review", "reviewed", "dismissed"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_event_or_404(event_id: uuid.UUID, db: Session) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def _event_to_response(event: Event) -> EventResponse:
    return EventResponse(
        id=event.id,
        video_id=event.video_id,
        event_index=event.event_index,
        start_pts_ms=event.start_pts_ms,
        end_pts_ms=event.end_pts_ms,
        peak_motion_score=event.peak_motion_score,
        total_motion_area=event.total_motion_area,
        event_status=event.event_status,
        has_thumbnail=bool(event.thumbnail_path),
        has_clip=bool(event.clip_path),
    )


# ---------------------------------------------------------------------------
# Routes — events by video
# ---------------------------------------------------------------------------


@router.get(
    "/videos/{video_id}/events",
    response_model=list[EventResponse],
    summary="List events for a video",
)
def list_events(
    video_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    event_status: Optional[str] = Query(default=None, alias="status"),
) -> list[EventResponse]:
    """Return all events for a video, optionally filtered by status."""
    if event_status is not None and event_status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"status must be one of {sorted(_VALID_STATUSES)}",
        )

    query = db.query(Event).filter(Event.video_id == video_id)
    if event_status is not None:
        query = query.filter(Event.event_status == event_status)

    events = query.order_by(Event.event_index).all()
    return [_event_to_response(e) for e in events]


# ---------------------------------------------------------------------------
# Routes — single event
# ---------------------------------------------------------------------------


@router.get(
    "/events/{event_id}",
    response_model=EventResponse,
    summary="Single event detail with latest review",
)
def get_event(
    event_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> EventResponse:
    """Return full event detail.  Assets and latest review are embedded in the model."""
    event = _get_event_or_404(event_id, db)
    return _event_to_response(event)


# ---------------------------------------------------------------------------
# Routes — reviews
# ---------------------------------------------------------------------------


@router.post(
    "/events/{event_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update review for an event",
)
def create_review(
    event_id: uuid.UUID,
    body: ReviewRequest,
    reviewer: ReviewerUser,
    db: Annotated[Session, Depends(get_db)],
) -> ReviewResponse:
    """Upsert a review record for an event.  Marks event as 'reviewed'."""
    event = _get_event_or_404(event_id, db)

    review = Review(
        id=uuid.uuid4(),
        event_id=event.id,
        label_manual=body.label_manual,
        is_false_alarm=body.is_false_alarm,
        priority=body.priority,
        notes=body.notes,
        reviewer_id=reviewer.id,
    )
    db.add(review)

    event.event_status = "reviewed"
    db.commit()
    db.refresh(review)

    return ReviewResponse(
        id=review.id,
        event_id=review.event_id,
        label_manual=review.label_manual,
        is_false_alarm=review.is_false_alarm,
        priority=review.priority,
        notes=review.notes,
        reviewer_id=review.reviewer_id,
        created_at=review.created_at,
    )


# ---------------------------------------------------------------------------
# Routes — media assets
# ---------------------------------------------------------------------------


@router.get(
    "/events/{event_id}/thumbnail",
    summary="Serve event thumbnail (WebP)",
    response_class=FileResponse,
)
def get_thumbnail(
    event_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    """Stream the thumbnail WebP for an event."""
    event = _get_event_or_404(event_id, db)
    if not event.thumbnail_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not available")
    return FileResponse(path=event.thumbnail_path, media_type="image/webp")


@router.get(
    "/events/{event_id}/clip",
    summary="Serve event clip (MP4)",
    response_class=FileResponse,
)
def get_clip(
    event_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    """Stream the MP4 clip for an event."""
    event = _get_event_or_404(event_id, db)
    if not event.clip_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not available")
    return FileResponse(path=event.clip_path, media_type="video/mp4")
