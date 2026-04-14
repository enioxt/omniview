"""Generates synthetic test videos using FFmpeg.

Creates minimal MP4s with known motion patterns so tests are deterministic
and don't require real surveillance footage.

Usage:
    python tests/fixtures/generate_videos.py
"""
from __future__ import annotations

import subprocess
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent


def make_static_video(path: Path, duration_s: int = 10, fps: int = 30) -> Path:
    """Static background, no movement — should produce 0 events."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s=640x480:r={fps}:d={duration_s}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return path


def make_motion_video(path: Path, duration_s: int = 10, fps: int = 30) -> Path:
    """Moving white rectangle on dark background — should produce ≥1 event."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Animate a white rectangle moving across the frame
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", (
            f"color=c=0x111111:s=640x480:r={fps}:d={duration_s},"
            "drawbox=x='100+t*30':y=200:w=80:h=80:color=white:t=fill"
        ),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return path


if __name__ == "__main__":
    make_static_video(FIXTURES_DIR / "static_10s.mp4")
    make_motion_video(FIXTURES_DIR / "motion_10s.mp4")
    print("Fixtures generated:", FIXTURES_DIR)
