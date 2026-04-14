# OmniView — Architecture

## Principles

1. **Local-first** — works fully offline, no cloud required
2. **Immutable originals** — source file never modified after ingest
3. **Auditable** — every action logged; every derivative links to original SHA-256
4. **Modular** — core works without heavy detector or LLM
5. **Motion-first gating** — heavy detector only fires after motion threshold

## Layer Model

```
Layer A — Original evidence
  original file (read-only) + SHA-256 + ingest metadata

Layer B — Derived events (auditable)
  motion events + thumbnails + clips + detection results
  every asset links back to original SHA-256

Layer C — Human review (versioned)
  manual labels + priority + notes + reviewer + timestamp

Layer D — Analytical artifacts (optional)
  export packages + HTML reports + synopsis (R&D)
```

## Topology

```
[Video files / watch folder]
        │
        ▼
[Python Engine — FastAPI :8000]
  ├── ingest (hash, quarantine, copy)
  ├── motion pipeline (MOG2 + ROI + event grouping)
  ├── thumbnails + clips (FFmpeg)
  ├── detector (optional — YOLO11n)
  ├── export (ZIP + HTML + provenance)
  └── SQLite WAL
        │
        ▼
[React UI — :5173 (dev) / :80 (prod)]
  ├── VideoPlayer + Timeline
  ├── EventGallery + ReviewPanel
  └── Export page
```

## Motion Gating Formula

```
S_motion = (1 / A) * Σ |I_t(x,y) - B_t(x,y)|

where:
  I_t  = current frame intensity
  B_t  = MOG2 background model
  A    = contour area

Detector only fires when:
  S_motion > σ1  AND  contour_area > σ2
```

## Database (SQLite WAL)

Tables: `videos`, `video_metadata`, `events`, `event_assets`,
`detections`, `reviews`, `audit_logs`, `retention_policies`, `users`

Migration tool: Alembic. Ready to switch to Postgres (same schema).

## File Storage

```
storage/
  originals/   — read-only after ingest
  working/     — working copies
  thumbnails/  — WebP, one per event
  clips/       — short MP4s per event (optional)
  exports/     — signed ZIP/HTML packages
  quarantine/  — pending validation
  logs/        — structured JSON logs
```
