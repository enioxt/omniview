"""Provenance service — writes and updates the chain-of-custody JSON.

The provenance file lives alongside exports and is regenerated on each
significant transform. Every output package includes a copy.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.db.models import Video


class ProvenanceService:
    @staticmethod
    def _path(video_id: str) -> Path:
        p = settings.working_path / "provenance"
        p.mkdir(parents=True, exist_ok=True)
        return p / f"{video_id}_provenance.json"

    @staticmethod
    def write_initial(video: Video) -> None:
        """Write initial provenance after ingest."""
        data: dict[str, object] = {
            "video_id": video.id,
            "original_sha256": video.sha256,
            "source_camera": video.source_name,
            "timezone": video.timezone,
            "ingested_by": video.ingested_by,
            "ingested_at": (video.ingested_at or datetime.now(timezone.utc)).isoformat(),
            "original_path": video.original_path,
            "working_copy_path": video.working_copy_path,
            "transforms": [],
        }
        ProvenanceService._path(video.id).write_text(json.dumps(data, indent=2))

    @staticmethod
    def append_transform(video_id: str, transform_type: str, detail: dict[str, object]) -> None:
        """Append a transform record to the provenance file."""
        path = ProvenanceService._path(video_id)
        if not path.exists():
            return
        data = json.loads(path.read_text())
        transforms: list[dict[str, object]] = data.get("transforms", [])
        transforms.append(
            {
                "type": transform_type,
                "at": datetime.now(timezone.utc).isoformat(),
                **detail,
            }
        )
        data["transforms"] = transforms
        path.write_text(json.dumps(data, indent=2))

    @staticmethod
    def read(video_id: str) -> dict[str, object]:
        path = ProvenanceService._path(video_id)
        if not path.exists():
            return {}
        return json.loads(path.read_text())  # type: ignore[return-value]
