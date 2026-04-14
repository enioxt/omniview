"""FFprobe wrapper — extract video metadata without loading frames."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.errors import VideoCorrupt


@dataclass
class VideoInfo:
    duration_ms: int
    fps: float
    width: int
    height: int
    codec: str
    bit_rate: int | None
    creation_time: str | None
    container_format: str
    extra: dict[str, object]


def probe(path: Path) -> VideoInfo:
    """Run ffprobe and return structured video info.

    Raises VideoCorrupt if the file cannot be read.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise VideoCorrupt(detail=str(exc)) from exc

    if result.returncode != 0:
        raise VideoCorrupt(detail=result.stderr.strip()[:256])

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise VideoCorrupt(detail="ffprobe returned invalid JSON") from exc

    # Find first video stream
    video_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
        None,
    )
    if video_stream is None:
        raise VideoCorrupt(detail="No video stream found")

    fmt = data.get("format", {})
    duration_s = float(fmt.get("duration") or video_stream.get("duration") or 0)

    # FPS from r_frame_rate (e.g. "30/1" or "30000/1001")
    fps_raw: str = video_stream.get("r_frame_rate", "0/1")
    try:
        num, den = fps_raw.split("/")
        fps = float(num) / float(den) if float(den) else 0.0
    except (ValueError, ZeroDivisionError):
        fps = 0.0

    bit_rate_raw = fmt.get("bit_rate")
    bit_rate = int(bit_rate_raw) if bit_rate_raw else None

    return VideoInfo(
        duration_ms=int(duration_s * 1000),
        fps=round(fps, 3),
        width=int(video_stream.get("width", 0)),
        height=int(video_stream.get("height", 0)),
        codec=video_stream.get("codec_name", "unknown"),
        bit_rate=bit_rate,
        creation_time=fmt.get("tags", {}).get("creation_time"),
        container_format=fmt.get("format_name", "unknown"),
        extra={"streams": data.get("streams", [])},
    )
