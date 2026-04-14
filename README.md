# OmniView

Local-first video analysis system for security cameras.

- Ingest video files with SHA-256 integrity and full provenance
- Motion detection with configurable ROI and thresholds
- Event grouping with thumbnails and optional short clips
- Clickable timeline UI for human review and annotation
- Auditable ZIP/HTML export with chain-of-custody

## Quick start

```bash
# Backend
cd engine && pip install -e ".[dev]"
uvicorn app.main:app --reload

# Frontend
cd ui && npm install && npm run dev
```

## Stack

- **Backend:** Python 3.12, FastAPI, OpenCV, FFmpeg, SQLAlchemy, SQLite (WAL)
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS
- **Distribution:** Docker Compose (LAN server) or PyInstaller (single machine)

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## License

MIT
