"""Auto-conversion layer for DVR / proprietary video formats.

Problem: Police DVRs export footage in formats like .264, .dav, .h264, .ts
that OpenCV cannot reliably read.  This module detects whether a given file
needs conversion and, if so, re-encodes it to H.264 MP4 in the working
directory before ingest.

Design principles (OmniView):
- Original file is NEVER touched.
- Conversion is transparent — callers just call ``ensure_playable()``.
- Uses ffmpeg with CRF 18 to preserve visual quality.
- Graceful degradation: if ffmpeg is missing, returns the original path and
  logs a warning (OpenCV may still succeed for some containers).
"""
from __future__ import annotations

import logging
import subprocess
import shutil
from pathlib import Path

from app.core.errors import VideoCorrupt

logger = logging.getLogger(__name__)

# Extensions that browsers / OpenCV typically cannot handle natively.
# ffprobe can still read them, but a re-wrap or transcode is required.
_NEEDS_CONVERSION: frozenset[str] = frozenset({
    ".264", ".h264", ".dav", ".dvr", ".m2ts", ".mts",
    ".asf", ".wmv", ".flv",
})

# Codecs that OpenCV's VideoCapture struggles with even inside .avi containers.
_NEEDS_TRANSCODE_CODEC: frozenset[str] = frozenset({
    "hevc", "h265", "mpeg2video", "mjpeg", "vp9",
    "wmv1", "wmv2", "flv1", "theora",
})


def needs_conversion(path: Path, codec: str = "") -> bool:
    """Return True if the file should be converted before processing."""
    if path.suffix.lower() in _NEEDS_CONVERSION:
        return True
    if codec and codec.lower() in _NEEDS_TRANSCODE_CODEC:
        return True
    return False


def ensure_playable(source: Path, working_dir: Path) -> Path:
    """Return a path to an H.264 MP4 version of *source*.

    If conversion is not needed, returns *source* unchanged.
    If ffmpeg is unavailable, logs a warning and returns *source* (best effort).

    The converted file is placed at:
        ``working_dir / "converted" / "<stem>.mp4"``

    Raises:
        VideoCorrupt: if ffmpeg is present but the conversion fails.
    """
    if not needs_conversion(source):
        return source

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        logger.warning(
            "converter: ffmpeg not found — processing %s as-is (may fail)", source.name
        )
        return source

    out_dir = working_dir / "converted"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / (source.stem + ".mp4")

    if dest.exists():
        logger.info("converter: cached conversion found at %s", dest)
        return dest

    logger.info("converter: converting %s → %s", source.name, dest.name)
    cmd = [
        ffmpeg,
        "-y",                   # overwrite silently
        "-i", str(source),
        "-c:v", "libx264",
        "-crf", "18",           # visually lossless
        "-preset", "fast",
        "-c:a", "aac",
        "-movflags", "+faststart",
        "-loglevel", "error",
        str(dest),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,        # 10 min max for 1h video
        )
    except subprocess.TimeoutExpired as exc:
        raise VideoCorrupt(
            detail=f"Conversion timeout after 600s for {source.name}"
        ) from exc
    except FileNotFoundError as exc:
        logger.warning("converter: ffmpeg not executable — %s", exc)
        return source

    if result.returncode != 0:
        stderr = result.stderr.strip()[:512]
        raise VideoCorrupt(
            detail=f"Conversion failed for {source.name}: {stderr}"
        )

    logger.info("converter: ✓ %s ready (%s)", dest.name, _human_size(dest))
    return dest


# ── helpers ───────────────────────────────────────────────────────────────────

def _human_size(path: Path) -> str:
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size //= 1024
    return f"{size:.0f} TB"
