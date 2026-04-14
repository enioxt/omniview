"""Motion detection pipeline.

Algorithm: MOG2 background subtraction with dual-threshold gating.

  S_motion = (1 / A) * Σ |I_t(x,y) - B_t(x,y)|

  Gate: S_motion > σ1  AND  contour_area > σ2

Streams frames — never loads the full video into RAM.
Yields MotionFrame objects for each frame above threshold.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

import cv2
import numpy as np

from app.core.config import settings
from app.core.errors import MotionPipelineError


@dataclass
class MotionFrame:
    """A single frame that passed motion gating."""
    frame_index: int
    pts_ms: int          # presentation timestamp in ms
    motion_score: float  # S_motion value
    contour_area: float  # largest contour area (pixels)
    bboxes: list[tuple[int, int, int, int]] = field(default_factory=list)  # (x,y,w,h)


@dataclass
class MotionConfig:
    score_threshold: float = settings.motion_score_threshold    # σ1
    min_area: int = settings.motion_min_area                    # σ2
    sample_every: int = settings.motion_sample_every            # 1/N frames
    # MOG2 params
    history: int = 500
    var_threshold: float = 16.0
    detect_shadows: bool = False
    # ROI mask path (optional — grayscale PNG, white=active)
    roi_mask_path: str | None = None


def scan_video(
    video_path: Path,
    config: MotionConfig | None = None,
    progress_callback: object = None,  # callable(frame_idx, total_frames) | None
) -> Generator[MotionFrame, None, None]:
    """Stream through a video file and yield frames with significant motion.

    Args:
        video_path: Path to the video file (working copy).
        config: Motion detection settings. Uses global defaults if None.
        progress_callback: Optional callable(current_frame, total_frames).

    Yields:
        MotionFrame for each sampled frame that passes both thresholds.

    Raises:
        MotionPipelineError: If the video cannot be opened or read.
    """
    cfg = config or MotionConfig()

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise MotionPipelineError(detail=f"Cannot open video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

    # Background subtractor
    bg_sub = cv2.createBackgroundSubtractorMOG2(
        history=cfg.history,
        varThreshold=cfg.var_threshold,
        detectShadows=cfg.detect_shadows,
    )

    # Optional ROI mask
    roi_mask: np.ndarray | None = None
    if cfg.roi_mask_path:
        roi_mask = cv2.imread(cfg.roi_mask_path, cv2.IMREAD_GRAYSCALE)

    frame_index = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_index += 1

            if progress_callback is not None:
                progress_callback(frame_index, total_frames)  # type: ignore[operator]

            # Sample every N frames
            if frame_index % cfg.sample_every != 0:
                continue

            # PTS: estimate from frame index and FPS
            pts_ms = int((frame_index / fps) * 1000)

            # Apply ROI mask if provided
            if roi_mask is not None:
                frame = cv2.bitwise_and(frame, frame, mask=roi_mask)

            # Background subtraction → foreground mask
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            fg_mask = bg_sub.apply(gray)

            # Find contours in foreground mask
            contours, _ = cv2.findContours(
                fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if not contours:
                continue

            # Compute motion score: mean absolute foreground intensity
            total_pixels = fg_mask.size or 1
            motion_score = float(np.sum(fg_mask > 0)) / total_pixels * 255.0

            # Largest contour area
            max_area = max(cv2.contourArea(c) for c in contours)

            # Dual-threshold gate
            if motion_score < cfg.score_threshold or max_area < cfg.min_area:
                continue

            # Extract bounding boxes for significant contours
            bboxes = [
                cv2.boundingRect(c)
                for c in contours
                if cv2.contourArea(c) >= cfg.min_area
            ]

            yield MotionFrame(
                frame_index=frame_index,
                pts_ms=pts_ms,
                motion_score=round(motion_score, 4),
                contour_area=round(max_area, 2),
                bboxes=bboxes,
            )

    finally:
        cap.release()
