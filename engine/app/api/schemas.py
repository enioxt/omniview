"""Pydantic response/request schemas for the OmniView API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Video
# ---------------------------------------------------------------------------


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    sha256: str
    source_name: str
    duration_ms: Optional[int]
    fps_nominal: Optional[float]
    width: Optional[int]
    height: Optional[int]
    ingested_at: datetime
    event_count: int


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    video_id: uuid.UUID
    event_index: int
    start_pts_ms: int
    end_pts_ms: int
    peak_motion_score: float
    total_motion_area: float
    event_status: str
    has_thumbnail: bool
    has_clip: bool


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------


class ReviewRequest(BaseModel):
    label_manual: Optional[str] = None
    is_false_alarm: bool
    priority: str
    notes: Optional[str] = None


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    label_manual: Optional[str]
    is_false_alarm: bool
    priority: str
    notes: Optional[str]
    reviewer_id: uuid.UUID
    created_at: datetime


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    code: str
    message: str
    correlation_id: Optional[str] = None
