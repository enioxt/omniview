"""Short clip extraction — uses FFmpeg to cut ±seconds around an event.

The clip is a copy without re-encoding (stream copy) for speed and quality.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from app.core.config import settings
from app.core.errors import MotionPipelineError
from app.core.integrity import sha256_file


def extract_clip(
    video_path: Path,
    event_start_ms: int,
    event_end_ms: int,
    output_path: Path,
    pre_seconds: float = settings.clip_pre_seconds,
    post_seconds: float = settings.clip_post_seconds,
) -> str:
    """Extract a short clip around an event using FFmpeg stream copy.

    Args:
        video_path: Source video (working copy).
        event_start_ms: Event start in milliseconds (PTS).
        event_end_ms: Event end in milliseconds (PTS).
        output_path: Destination MP4 path.
        pre_seconds: Seconds before event start to include.
        post_seconds: Seconds after event end to include.

    Returns:
        SHA-256 of the saved clip.

    Raises:
        MotionPipelineError on FFmpeg failure.
    """
    start_s = max(0.0, event_start_ms / 1000.0 - pre_seconds)
    end_s = event_end_ms / 1000.0 + post_seconds
    duration_s = end_s - start_s

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-ss", f"{start_s:.3f}",
        "-i", str(video_path),
        "-t", f"{duration_s:.3f}",
        "-c", "copy",          # stream copy — no re-encoding
        "-movflags", "+faststart",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise MotionPipelineError(detail=f"FFmpeg clip error: {result.stderr.strip()[:256]}")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise MotionPipelineError(detail="FFmpeg produced empty clip file")

    return sha256_file(output_path)
