"""Event grouping — merges nearby motion frames into discrete events.

Rules:
  - A new event starts when a MotionFrame arrives after a gap > gap_ms.
  - Events shorter than min_duration_ms are discarded.
  - The peak frame (highest motion_score) becomes the thumbnail source.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from app.core.config import settings
from app.core.motion import MotionFrame


@dataclass
class MotionEvent:
    """A discrete motion event derived from grouped MotionFrames."""
    start_frame: int
    end_frame: int
    start_pts_ms: int
    end_pts_ms: int
    peak_frame: int
    peak_pts_ms: int
    peak_motion_score: float
    total_motion_area: float
    frame_count: int
    bboxes_at_peak: list[tuple[int, int, int, int]] = field(default_factory=list)

    @property
    def duration_ms(self) -> int:
        return self.end_pts_ms - self.start_pts_ms


def group_motion_frames(
    frames: Iterable[MotionFrame],
    gap_ms: int = settings.motion_gap_ms,
    min_duration_ms: int = settings.motion_min_duration_ms,
) -> list[MotionEvent]:
    """Group an iterable of MotionFrames into discrete MotionEvents.

    Args:
        frames: Sorted MotionFrame objects from scan_video().
        gap_ms: If two frames are more than gap_ms apart, start a new event.
        min_duration_ms: Discard events shorter than this (noise filter).

    Returns:
        List of MotionEvent, sorted by start_pts_ms.
    """
    events: list[MotionEvent] = []
    current: _Builder | None = None

    for mf in frames:
        if current is None:
            current = _Builder(mf)
        elif mf.pts_ms - current.last_pts_ms > gap_ms:
            # Gap too large — close current event, start new one
            evt = current.build()
            if evt.duration_ms >= min_duration_ms:
                events.append(evt)
            current = _Builder(mf)
        else:
            current.add(mf)

    # Close last event
    if current is not None:
        evt = current.build()
        if evt.duration_ms >= min_duration_ms:
            events.append(evt)

    return events


class _Builder:
    """Accumulates MotionFrames into a single event."""

    def __init__(self, first: MotionFrame) -> None:
        self.start_frame = first.frame_index
        self.start_pts_ms = first.pts_ms
        self.last_pts_ms = first.pts_ms
        self.end_frame = first.frame_index
        self.end_pts_ms = first.pts_ms
        self.peak = first
        self.total_area = first.contour_area
        self.count = 1

    def add(self, mf: MotionFrame) -> None:
        self.end_frame = mf.frame_index
        self.end_pts_ms = mf.pts_ms
        self.last_pts_ms = mf.pts_ms
        self.total_area += mf.contour_area
        self.count += 1
        if mf.motion_score > self.peak.motion_score:
            self.peak = mf

    def build(self) -> MotionEvent:
        return MotionEvent(
            start_frame=self.start_frame,
            end_frame=self.end_frame,
            start_pts_ms=self.start_pts_ms,
            end_pts_ms=self.end_pts_ms,
            peak_frame=self.peak.frame_index,
            peak_pts_ms=self.peak.pts_ms,
            peak_motion_score=round(self.peak.motion_score, 4),
            total_motion_area=round(self.total_area, 2),
            frame_count=self.count,
            bboxes_at_peak=self.peak.bboxes,
        )
