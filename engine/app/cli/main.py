"""OmniView CLI — headless operations for batch processing."""
from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def cli() -> None:
    """OmniView — local video analysis CLI."""


@cli.command()
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option("--camera", "-c", required=True, help="Camera / source name")
@click.option("--operator", "-o", default="cli", show_default=True, help="Operator name")
@click.option("--timezone", "-tz", default="America/Sao_Paulo", show_default=True)
@click.option("--no-scan", is_flag=True, default=False, help="Ingest only, skip motion scan")
def ingest(
    video_path: Path,
    camera: str,
    operator: str,
    timezone: str,
    no_scan: bool,
) -> None:
    """Ingest a video file and run motion scan."""
    from app.db.base import SessionLocal, init_db
    from app.core.ingest import ingest_file
    from app.workers.scan_worker import process_video

    init_db()
    db = SessionLocal()

    try:
        console.print(f"[cyan]Ingesting[/cyan] {video_path}…")
        video = ingest_file(
            video_path,
            db=db,
            source_name=camera,
            operator_id=operator,
            timezone_str=timezone,
        )
        console.print(f"[green]✓[/green] Ingested — ID: [bold]{video.id}[/bold]  SHA-256: {video.sha256}")

        if not no_scan:
            console.print("[cyan]Running motion scan…[/cyan]")
            events = process_video(video, db)
            console.print(f"[green]✓[/green] Found [bold]{len(events)}[/bold] motion events")
    except Exception as exc:
        console.print(f"[red]✗ Error:[/red] {exc}")
        raise SystemExit(1)
    finally:
        db.close()


@cli.command()
@click.argument("video_id")
def process(video_id: str) -> None:
    """Run motion scan on an already-ingested video."""
    from app.db.base import SessionLocal
    from app.db.models import Video
    from app.workers.scan_worker import process_video

    db = SessionLocal()
    try:
        video = db.get(Video, video_id)
        if video is None:
            console.print(f"[red]Video {video_id} not found[/red]")
            raise SystemExit(1)

        console.print(f"[cyan]Processing[/cyan] {video.source_name} ({video_id})…")
        events = process_video(video, db)
        console.print(f"[green]✓[/green] {len(events)} events")
    finally:
        db.close()


@cli.command("list")
def list_videos() -> None:
    """List all ingested videos."""
    from app.db.base import SessionLocal
    from app.db.models import Event, Video

    db = SessionLocal()
    try:
        videos = db.query(Video).order_by(Video.ingested_at.desc()).all()
        if not videos:
            console.print("[yellow]No videos ingested yet.[/yellow]")
            return

        table = Table(title="Videos")
        table.add_column("ID", style="dim", width=36)
        table.add_column("Camera")
        table.add_column("Status")
        table.add_column("Duration")
        table.add_column("Events", justify="right")

        for v in videos:
            dur = f"{v.duration_ms // 60000}m{(v.duration_ms % 60000) // 1000}s" if v.duration_ms else "?"
            count = db.query(Event).filter(Event.video_id == v.id).count()
            table.add_row(v.id, v.source_name or "?", v.status, dur, str(count))

        console.print(table)
    finally:
        db.close()


@cli.command()
@click.argument("video_id")
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None,
              help="Output path for ZIP (default: exports/ dir)")
def export(video_id: str, output: Path | None) -> None:
    """Export a forensic ZIP for a completed video."""
    from app.db.base import SessionLocal, init_db
    from app.services.export_service import ExportService

    init_db()
    db = SessionLocal()
    try:
        svc = ExportService(db)
        zip_path = svc.export_video(video_id)
        if output:
            import shutil
            shutil.move(str(zip_path), str(output))
            zip_path = output
        console.print(f"[green]✓[/green] Export created: [bold]{zip_path}[/bold]")
    except ValueError as exc:
        console.print(f"[red]✗ Error:[/red] {exc}")
        raise SystemExit(1)
    finally:
        db.close()


@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def verify(path: Path) -> None:
    """Verify integrity of a file or exported ZIP.

    For raw files: prints SHA-256.
    For ZIP exports: verifies HMAC manifest signature.
    """
    if path.suffix.lower() == ".zip":
        from app.services.export_service import ExportService
        ok = ExportService.verify_zip(path)
        if ok:
            console.print(f"[green]✓ VALID[/green] — manifest HMAC verified: {path.name}")
        else:
            console.print(f"[red]✗ INVALID[/red] — manifest signature mismatch or file tampered: {path.name}")
            raise SystemExit(1)
    else:
        from app.core.integrity import sha256_file
        sha = sha256_file(path)
        console.print(f"SHA-256: [bold]{sha}[/bold]")


@cli.command()
@click.option("--dry-run", is_flag=True, default=False,
              help="Preview what would be purged without deleting")
def retention(dry_run: bool) -> None:
    """Purge videos past their retention window."""
    from app.db.base import SessionLocal, init_db
    from app.core.retention import run_retention

    init_db()
    db = SessionLocal()
    try:
        label = "[yellow]DRY RUN[/yellow] " if dry_run else ""
        console.print(f"{label}[cyan]Running retention sweep…[/cyan]")
        counts = run_retention(db, dry_run=dry_run)
        console.print(
            f"[green]✓[/green] checked={counts['checked']} "
            f"purged={counts['purged']} skipped={counts['skipped']} errors={counts['errors']}"
        )
    finally:
        db.close()
