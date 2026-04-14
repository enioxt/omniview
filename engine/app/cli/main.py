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
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
def verify(video_path: Path) -> None:
    """Verify SHA-256 integrity of a file."""
    from app.core.integrity import sha256_file
    sha = sha256_file(video_path)
    console.print(f"SHA-256: [bold]{sha}[/bold]")
