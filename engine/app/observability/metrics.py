"""Prometheus metrics exposed at /api/metrics."""
from __future__ import annotations

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

videos_ingested = Counter("omniview_videos_ingested_total", "Videos successfully ingested")
events_generated = Counter("omniview_events_generated_total", "Motion events generated")
detector_calls = Counter("omniview_detector_calls_total", "Heavy detector invocations")
exports_created = Counter("omniview_exports_created_total", "Export packages created")

ingestion_duration = Histogram(
    "omniview_ingestion_duration_seconds",
    "Time to ingest and hash a video",
    buckets=[1, 5, 10, 30, 60, 120, 300],
)
scan_duration = Histogram(
    "omniview_scan_duration_seconds",
    "Time to run motion scan on a video",
    buckets=[5, 15, 30, 60, 120, 300, 600],
)
motion_score_dist = Histogram(
    "omniview_motion_score",
    "Distribution of motion scores at detection",
    buckets=[5, 10, 25, 50, 100, 200],
)


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
