"""ytf — command-line interface for the video pipeline."""

from __future__ import annotations

import logging

import typer
from rich.console import Console
from rich.table import Table

from yt_factory import pipeline
from yt_factory.config import load_secrets, load_settings
from yt_factory.logging import setup_logging
from yt_factory.stages import ALL_STAGES, STAGE_NAMES
from yt_factory.workspace import StageStatus, Workspace

app = typer.Typer(help="Personal AI YouTube video factory.", no_args_is_help=True)
console = Console()
log = logging.getLogger(__name__)

_STATUS_STYLE = {
    StageStatus.DONE: "green",
    StageStatus.RUNNING: "yellow",
    StageStatus.FAILED: "red",
    StageStatus.PENDING: "dim",
    StageStatus.AWAITING_REVIEW: "cyan",
}


@app.callback()
def _init() -> None:
    setup_logging()


@app.command()
def new(topic: str = typer.Option(..., "--topic", help="Video topic")) -> None:
    """Create a new video workspace for TOPIC."""
    settings = load_settings()
    ws = Workspace.create(settings.paths.videos_dir, topic, STAGE_NAMES)
    console.print(f"[green]Created[/green] workspace [bold]{ws.video_id}[/bold]")
    console.print(f"Next: [bold]ytf run {ws.video_id}[/bold]")


@app.command()
def run(
    video_id: str,
    until: str | None = typer.Option(None, help=f"Stop after this stage ({', '.join(STAGE_NAMES)})"),
    ignore_gates: bool = typer.Option(False, help="Do not pause at review gates"),
) -> None:
    """Run pending pipeline stages for VIDEO_ID."""
    settings = load_settings()
    ws = Workspace.load(settings.paths.videos_dir, video_id)
    try:
        pipeline.run(ws, settings, load_secrets(), until=until, ignore_gates=ignore_gates)
    except pipeline.GateReached as gate:
        console.print(
            f"[cyan]Paused[/cyan] for review after stage [bold]{gate.stage_name}[/bold]. "
            f"Inspect the workspace, then continue with [bold]ytf run {video_id}[/bold]."
        )
        raise typer.Exit(0) from None
    except Exception:
        console.print(f"[red]Stage failed.[/red] See log; retry with [bold]ytf run {video_id}[/bold].")
        raise typer.Exit(1) from None
    console.print("[green]All requested stages complete.[/green]")


@app.command()
def retry(video_id: str, stage: str) -> None:
    """Re-run one STAGE for VIDEO_ID, even if it already succeeded."""
    settings = load_settings()
    ws = Workspace.load(settings.paths.videos_dir, video_id)
    matching = [s for s in ALL_STAGES if s.name == stage]
    if not matching:
        console.print(f"[red]Unknown stage[/red] '{stage}'. Stages: {', '.join(STAGE_NAMES)}")
        raise typer.Exit(2)
    pipeline.run_stage(matching[0], ws, settings, load_secrets())
    console.print(f"[green]Stage '{stage}' done.[/green]")


@app.command()
def status(video_id: str) -> None:
    """Show stage-by-stage status for VIDEO_ID."""
    settings = load_settings()
    ws = Workspace.load(settings.paths.videos_dir, video_id)
    manifest = ws.manifest()
    table = Table(title=f"{manifest.video_id} — {manifest.topic or ''}")
    table.add_column("stage")
    table.add_column("status")
    table.add_column("error")
    for name in STAGE_NAMES:
        record = manifest.stages.get(name)
        if record is None:
            continue
        style = _STATUS_STYLE[record.status]
        table.add_row(name, f"[{style}]{record.status}[/{style}]", record.error or "")
    console.print(table)


@app.command(name="list")
def list_videos() -> None:
    """List all video workspaces."""
    settings = load_settings()
    workspaces = Workspace.list_all(settings.paths.videos_dir)
    if not workspaces:
        console.print("No videos yet. Start with [bold]ytf new --topic '...'[/bold]")
        return
    table = Table(title="videos")
    table.add_column("video id")
    table.add_column("topic")
    table.add_column("progress")
    for ws in workspaces:
        manifest = ws.manifest()
        done = sum(1 for r in manifest.stages.values() if r.status == StageStatus.DONE)
        table.add_row(manifest.video_id, manifest.topic or "", f"{done}/{len(manifest.stages)}")
    console.print(table)
