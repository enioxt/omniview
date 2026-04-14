"""Integration tests — motion scan on synthetic videos.

Requires FFmpeg to be installed and fixture videos generated.
"""
from pathlib import Path

import pytest

from app.core.event_grouping import group_motion_frames
from app.core.motion import MotionConfig, scan_video

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(scope="module")
def static_video() -> Path:
    p = FIXTURES / "static_10s.mp4"
    if not p.exists():
        pytest.skip("static_10s.mp4 not generated — run tests/fixtures/generate_videos.py")
    return p


@pytest.fixture(scope="module")
def motion_video() -> Path:
    p = FIXTURES / "motion_10s.mp4"
    if not p.exists():
        pytest.skip("motion_10s.mp4 not generated — run tests/fixtures/generate_videos.py")
    return p


def test_static_video_no_events(static_video: Path) -> None:
    """A static black video should produce no motion events."""
    cfg = MotionConfig(score_threshold=25.0, min_area=500)
    frames = list(scan_video(static_video, config=cfg))
    events = group_motion_frames(frames)
    assert len(events) == 0


def test_motion_video_has_events(motion_video: Path) -> None:
    """A video with a moving rectangle should produce at least 1 event."""
    cfg = MotionConfig(score_threshold=5.0, min_area=100)
    frames = list(scan_video(motion_video, config=cfg))
    events = group_motion_frames(frames, min_duration_ms=0)
    assert len(events) >= 1


def test_motion_video_peak_score_positive(motion_video: Path) -> None:
    cfg = MotionConfig(score_threshold=5.0, min_area=100)
    frames = list(scan_video(motion_video, config=cfg))
    events = group_motion_frames(frames, min_duration_ms=0)
    assert all(e.peak_motion_score > 0 for e in events)


def test_events_chronological(motion_video: Path) -> None:
    cfg = MotionConfig(score_threshold=5.0, min_area=100)
    frames = list(scan_video(motion_video, config=cfg))
    events = group_motion_frames(frames, min_duration_ms=0)
    pts_list = [e.start_pts_ms for e in events]
    assert pts_list == sorted(pts_list)
