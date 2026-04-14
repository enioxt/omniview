"""Thumbnail extraction — saves WebP for the peak frame of each event."""
from __future__ import annotations

from pathlib import Path

import cv2

from app.core.config import settings
from app.core.errors import MotionPipelineError
from app.core.integrity import sha256_file


def extract_thumbnail(
    video_path: Path,
    frame_index: int,
    output_path: Path,
    quality: int = settings.thumbnail_quality,
) -> str:
    """Extract a single frame and save as WebP.

    Returns:
        SHA-256 of the saved thumbnail.

    Raises:
        MotionPipelineError if the frame cannot be read.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise MotionPipelineError(detail=f"Cannot open video for thumbnail: {video_path}")

    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index - 1)
        ret, frame = cap.read()
        if not ret or frame is None:
            raise MotionPipelineError(detail=f"Cannot read frame {frame_index}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        success = cv2.imwrite(
            str(output_path),
            frame,
            [cv2.IMWRITE_WEBP_QUALITY, quality],
        )
        if not success:
            raise MotionPipelineError(detail=f"Failed to write thumbnail: {output_path}")
    finally:
        cap.release()

    return sha256_file(output_path)
