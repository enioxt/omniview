"""Unit tests for event grouping logic."""
import pytest

from app.core.event_grouping import group_motion_frames
from app.core.motion import MotionFrame


def _frame(idx: int, pts_ms: int, score: float = 30.0, area: float = 1000.0) -> MotionFrame:
    return MotionFrame(frame_index=idx, pts_ms=pts_ms, motion_score=score, contour_area=area)


def test_single_frame_becomes_event() -> None:
    frames = [_frame(10, 1000)]
    events = group_motion_frames(frames, gap_ms=2000, min_duration_ms=0)
    assert len(events) == 1
    assert events[0].start_pts_ms == 1000
    assert events[0].end_pts_ms == 1000


def test_nearby_frames_merge() -> None:
    frames = [_frame(10, 1000), _frame(11, 1500), _frame(12, 2000)]
    events = group_motion_frames(frames, gap_ms=2000, min_duration_ms=0)
    assert len(events) == 1
    assert events[0].start_pts_ms == 1000
    assert events[0].end_pts_ms == 2000
    assert events[0].frame_count == 3


def test_gap_creates_two_events() -> None:
    frames = [_frame(1, 1000), _frame(2, 1500), _frame(10, 10000), _frame(11, 10500)]
    events = group_motion_frames(frames, gap_ms=2000, min_duration_ms=0)
    assert len(events) == 2


def test_peak_frame_is_highest_score() -> None:
    frames = [
        _frame(1, 1000, score=20.0),
        _frame(2, 1300, score=80.0),
        _frame(3, 1600, score=40.0),
    ]
    events = group_motion_frames(frames, gap_ms=2000, min_duration_ms=0)
    assert events[0].peak_frame == 2
    assert events[0].peak_motion_score == 80.0


def test_short_events_discarded() -> None:
    frames = [_frame(1, 1000), _frame(2, 1100)]  # 100ms duration
    events = group_motion_frames(frames, gap_ms=2000, min_duration_ms=500)
    assert len(events) == 0


def test_empty_input() -> None:
    assert group_motion_frames([]) == []


def test_total_area_accumulates() -> None:
    frames = [_frame(1, 1000, area=500), _frame(2, 1500, area=700), _frame(3, 2000, area=300)]
    events = group_motion_frames(frames, gap_ms=2000, min_duration_ms=0)
    assert events[0].total_motion_area == pytest.approx(1500.0)
