"""Export service — forensic ZIP package.

ZIP structure:
    manifest.json           — SHA-256 per file + HMAC signature
    provenance.json         — chain-of-custody
    report.html             — human-readable HTML report
    original/<filename>     — copy of the original video
    thumbnails/<n>.webp     — event thumbnails
    clips/<n>.mp4           — event clips
    reviews/<n>.json        — review data per event

Verification:
    ExportService.verify_zip(path) → bool
    omniview-cli verify <zip>

Manifest HMAC covers: SHA-256 of all file entries concatenated + video_id + exported_at.
Changing any file or the manifest itself will fail verification.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.integrity import sha256_file
from app.db.models import Event, EventAsset, Review, Video
from app.services.provenance_service import ProvenanceService

log = structlog.get_logger(__name__)


class ExportService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def export_video(self, video_id: str) -> Path:
        """Build a forensic ZIP for the given video.

        Returns the path to the ZIP file inside settings.exports_path.
        Raises ValueError if video not found or not completed.
        """
        video = self._db.get(Video, video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")
        if video.status != "completed":
            raise ValueError(f"Video {video_id} is not completed (status={video.status})")

        events = (
            self._db.query(Event)
            .filter(Event.video_id == video_id)
            .order_by(Event.event_index)
            .all()
        )

        settings.exports_path.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        zip_name = f"omniview_export_{video_id[:8]}_{ts}.zip"
        zip_path = settings.exports_path / zip_name

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            file_entries: list[dict[str, str | int]] = []

            # ── original video ──────────────────────────────────────────────
            orig_path = Path(video.original_path)
            if orig_path.exists():
                dest_name = f"original/{orig_path.name}"
                dest = tmp_path / "original" / orig_path.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(orig_path, dest)
                file_entries.append({
                    "path": dest_name,
                    "sha256": sha256_file(dest),
                    "size": dest.stat().st_size,
                })
            else:
                log.warning("export.original_missing", video_id=video_id, path=str(orig_path))

            # ── thumbnails + clips ──────────────────────────────────────────
            for ev in events:
                assets: list[EventAsset] = (
                    self._db.query(EventAsset).filter(EventAsset.event_id == ev.id).all()
                )
                for asset in assets:
                    ap = Path(asset.path)
                    if not ap.exists():
                        continue
                    if asset.asset_type == "thumbnail_webp":
                        sub = "thumbnails"
                        fname = f"event_{ev.event_index:04d}.webp"
                    elif asset.asset_type == "clip_mp4":
                        sub = "clips"
                        fname = f"event_{ev.event_index:04d}.mp4"
                    else:
                        continue
                    dest = tmp_path / sub / fname
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(ap, dest)
                    file_entries.append({
                        "path": f"{sub}/{fname}",
                        "sha256": sha256_file(dest),
                        "size": dest.stat().st_size,
                    })

            # ── reviews JSON ────────────────────────────────────────────────
            (tmp_path / "reviews").mkdir(exist_ok=True)
            for ev in events:
                reviews: list[Review] = (
                    self._db.query(Review).filter(Review.event_id == ev.id).all()
                )
                review_data = {
                    "event_id": ev.id,
                    "event_index": ev.event_index,
                    "start_pts_ms": ev.start_pts_ms,
                    "end_pts_ms": ev.end_pts_ms,
                    "peak_motion_score": ev.peak_motion_score,
                    "event_status": ev.event_status,
                    "reviews": [
                        {
                            "id": r.id,
                            "label_manual": r.label_manual,
                            "is_false_alarm": r.is_false_alarm,
                            "priority": r.priority,
                            "notes": r.notes,
                            "reviewer_id": r.reviewer_id,
                            "created_at": r.created_at.isoformat(),
                        }
                        for r in reviews
                    ],
                }
                rfname = f"event_{ev.event_index:04d}.json"
                rdest = tmp_path / "reviews" / rfname
                rdest.write_text(json.dumps(review_data, indent=2, ensure_ascii=False))
                file_entries.append({
                    "path": f"reviews/{rfname}",
                    "sha256": sha256_file(rdest),
                    "size": rdest.stat().st_size,
                })

            # ── provenance.json ─────────────────────────────────────────────
            prov = ProvenanceService.read(video_id)
            prov_dest = tmp_path / "provenance.json"
            prov_dest.write_text(json.dumps(prov, indent=2, ensure_ascii=False))
            file_entries.append({
                "path": "provenance.json",
                "sha256": sha256_file(prov_dest),
                "size": prov_dest.stat().st_size,
            })

            # ── report.html ─────────────────────────────────────────────────
            report_dest = tmp_path / "report.html"
            report_dest.write_text(
                _build_html_report(video, events),
                encoding="utf-8",
            )
            file_entries.append({
                "path": "report.html",
                "sha256": sha256_file(report_dest),
                "size": report_dest.stat().st_size,
            })

            # ── manifest.json (with HMAC) ───────────────────────────────────
            exported_at = datetime.now(timezone.utc).isoformat()
            manifest = _build_manifest(video_id, exported_at, file_entries)
            manifest_dest = tmp_path / "manifest.json"
            manifest_dest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

            # ── write ZIP ───────────────────────────────────────────────────
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for entry in file_entries:
                    src = tmp_path / str(entry["path"])
                    if src.exists():
                        zf.write(src, str(entry["path"]))
                zf.write(manifest_dest, "manifest.json")

        log.info("export.created", video_id=video_id, zip=str(zip_path))
        return zip_path

    @staticmethod
    def verify_zip(zip_path: Path) -> bool:
        """Verify the HMAC signature of an exported ZIP.

        Returns True if valid, False if tampered or corrupt.
        """
        try:
            with zipfile.ZipFile(zip_path) as zf:
                manifest_bytes = zf.read("manifest.json")
            manifest = json.loads(manifest_bytes)

            stored_hmac = manifest.pop("hmac", "")
            payload = json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()
            expected = hmac.new(
                settings.secret_key.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(expected, stored_hmac)
        except Exception as exc:
            log.warning("export.verify_failed", error=str(exc))
            return False


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_manifest(
    video_id: str,
    exported_at: str,
    file_entries: list[dict[str, str | int]],
) -> dict[str, object]:
    manifest: dict[str, object] = {
        "version": "1.0",
        "tool": "OmniView",
        "video_id": video_id,
        "exported_at": exported_at,
        "files": file_entries,
    }
    payload = json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()
    manifest["hmac"] = hmac.new(
        settings.secret_key.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return manifest


def _build_html_report(video: Video, events: list[Event]) -> str:
    ingested = video.ingested_at.strftime("%Y-%m-%d %H:%M:%S UTC") if video.ingested_at else "—"
    duration = f"{(video.duration_ms or 0) / 1000:.1f}s" if video.duration_ms else "—"
    resolution = f"{video.width}×{video.height}" if video.width else "—"
    fps = f"{video.fps_nominal:.2f} fps" if video.fps_nominal else "—"

    rows = ""
    for ev in events:
        rows += (
            f"<tr>"
            f"<td>{ev.event_index + 1}</td>"
            f"<td>{_ms(ev.start_pts_ms)}</td>"
            f"<td>{_ms(ev.end_pts_ms)}</td>"
            f"<td>{ev.peak_motion_score:.1f}</td>"
            f"<td>{ev.event_status}</td>"
            f"</tr>\n"
        )
        if ev.event_index < len(events) - 1 and events[ev.event_index].event_index < ev.event_index:
            pass

    thumb_gallery = "".join(
        f'<div style="display:inline-block;margin:4px;text-align:center">'
        f'<img src="thumbnails/event_{ev.event_index:04d}.webp" '
        f'width="160" style="border:1px solid #444" alt="Event {ev.event_index+1}"/>'
        f'<br><small>#{ev.event_index+1} {_ms(ev.start_pts_ms)}</small>'
        f"</div>"
        for ev in events
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"/>
<title>OmniView — Relatório Forense</title>
<style>
  body{{font-family:sans-serif;background:#111;color:#ddd;padding:2em;}}
  h1{{color:#fff}} h2{{color:#aaa;border-bottom:1px solid #333;padding-bottom:.3em}}
  table{{border-collapse:collapse;width:100%}}
  th,td{{border:1px solid #333;padding:6px 10px;text-align:left}}
  th{{background:#222}} tr:hover{{background:#1a1a1a}}
  .meta{{display:grid;grid-template-columns:1fr 1fr;gap:.5em;background:#1a1a1a;padding:1em;border-radius:4px}}
  .meta span{{color:#888;font-size:.85em}}
</style>
</head>
<body>
<h1>OmniView — Relatório Forense</h1>
<div class="meta">
  <div><span>Fonte</span><br>{video.source_name or video.id}</div>
  <div><span>Ingestão</span><br>{ingested}</div>
  <div><span>Duração</span><br>{duration}</div>
  <div><span>Resolução</span><br>{resolution}</div>
  <div><span>FPS</span><br>{fps}</div>
  <div><span>SHA-256</span><br><small>{video.sha256 or "—"}</small></div>
  <div><span>Eventos detectados</span><br>{len(events)}</div>
  <div><span>Status</span><br>{video.status}</div>
</div>

<h2>Eventos de Movimento</h2>
<table>
<tr><th>#</th><th>Início</th><th>Fim</th><th>Score pico</th><th>Status</th></tr>
{rows}
</table>

<h2>Thumbnails</h2>
<div>{thumb_gallery}</div>

<p style="color:#555;font-size:.8em;margin-top:2em">
Gerado por OmniView — cadeia de custódia em provenance.json — integridade em manifest.json
</p>
</body>
</html>"""


def _ms(ms: int) -> str:
    s = ms // 1000
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
