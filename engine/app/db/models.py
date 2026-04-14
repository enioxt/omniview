"""OmniView database models.

Layer A — videos, video_metadata
Layer B — events, event_assets, detections
Layer C — reviews
Infra    — users, audit_logs, retention_policies
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Layer A — Evidence ─────────────────────────────────────────────────────────

class Video(Base):
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    original_path: Mapped[str] = mapped_column(String(512), nullable=False)
    working_copy_path: Mapped[str | None] = mapped_column(String(512))
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    file_size: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    fps_nominal: Mapped[float | None] = mapped_column(Float)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    source_name: Mapped[str | None] = mapped_column(String(128))
    timezone: Mapped[str] = mapped_column(String(64), default="America/Sao_Paulo")
    ingested_by: Mapped[str | None] = mapped_column(String(128))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    status: Mapped[str] = mapped_column(
        Enum(
            "uploaded", "hashing", "quarantine", "scanning",
            "processing", "completed", "failed",
            name="video_status",
        ),
        default="uploaded",
    )
    error_code: Mapped[str | None] = mapped_column(String(16))
    error_detail: Mapped[str | None] = mapped_column(Text)

    metadata_: Mapped[VideoMetadata | None] = relationship(
        "VideoMetadata", back_populates="video", uselist=False
    )
    events: Mapped[list[Event]] = relationship("Event", back_populates="video")

    __table_args__ = (Index("ix_videos_status", "status"),)


class VideoMetadata(Base):
    __tablename__ = "video_metadata"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    codec: Mapped[str | None] = mapped_column(String(32))
    bit_rate: Mapped[int | None] = mapped_column(Integer)
    creation_time: Mapped[str | None] = mapped_column(String(64))
    container_format: Mapped[str | None] = mapped_column(String(32))
    extra_json: Mapped[str | None] = mapped_column(Text)  # JSON blob

    video: Mapped[Video] = relationship("Video", back_populates="metadata_")


# ── Layer B — Derived events ───────────────────────────────────────────────────

class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    event_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_pts_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_pts_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    start_frame: Mapped[int] = mapped_column(Integer, nullable=False)
    end_frame: Mapped[int] = mapped_column(Integer, nullable=False)
    peak_motion_score: Mapped[float] = mapped_column(Float, nullable=False)
    peak_frame: Mapped[int] = mapped_column(Integer, nullable=False)
    total_motion_area: Mapped[float] = mapped_column(Float, default=0.0)
    detection_mode: Mapped[str] = mapped_column(
        Enum("motion_only", "motion_detector", "motion_detector_tracker", name="detection_mode"),
        default="motion_only",
    )
    event_status: Mapped[str] = mapped_column(
        Enum("pending_review", "reviewed", "dismissed", name="event_status"),
        default="pending_review",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    video: Mapped[Video] = relationship("Video", back_populates="events")
    assets: Mapped[list[EventAsset]] = relationship("EventAsset", back_populates="event")
    detections: Mapped[list[Detection]] = relationship("Detection", back_populates="event")
    reviews: Mapped[list[Review]] = relationship("Review", back_populates="event")

    __table_args__ = (
        Index("ix_events_video_id", "video_id"),
        UniqueConstraint("video_id", "event_index", name="uq_event_video_index"),
    )


class EventAsset(Base):
    __tablename__ = "event_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    asset_type: Mapped[str] = mapped_column(
        Enum("thumbnail_webp", "clip_mp4", "mask_png", name="asset_type"),
        nullable=False,
    )
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    event: Mapped[Event] = relationship("Event", back_populates="assets")


class Detection(Base):
    __tablename__ = "detections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    frame_ref: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    class_name: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x1: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y1: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x2: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y2: Mapped[float] = mapped_column(Float, nullable=False)
    tracker_id: Mapped[int | None] = mapped_column(Integer)
    backend_used: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    event: Mapped[Event] = relationship("Event", back_populates="detections")


# ── Layer C — Human review ─────────────────────────────────────────────────────

class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    reviewer_id: Mapped[str | None] = mapped_column(String(128))
    label_manual: Mapped[str | None] = mapped_column(
        Enum(
            "person", "vehicle_car", "vehicle_moto", "animal",
            "shadow", "bird", "false_alarm", "other",
            name="review_label",
        )
    )
    is_false_alarm: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", "critical", name="priority_level"),
        default="low",
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    event: Mapped[Event] = relationship("Event", back_populates="reviews")

    __table_args__ = (Index("ix_reviews_event_id", "event_id"),)


# ── Infrastructure ─────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("admin", "reviewer", "viewer", name="user_role"),
        default="reviewer",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditLog(Base):
    """Append-only audit trail. Never update or delete rows."""
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(128))
    payload_json: Mapped[str | None] = mapped_column(Text)
    row_hmac: Mapped[str | None] = mapped_column(String(64))  # HMAC-SHA256 for tamper detection
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)


class RetentionPolicy(Base):
    __tablename__ = "retention_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    camera_or_profile: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    noncritical_days: Mapped[int] = mapped_column(Integer, default=30)
    critical_days: Mapped[int] = mapped_column(Integer, default=365)
    keep_original_days: Mapped[int | None] = mapped_column(Integer)
    auto_delete_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
