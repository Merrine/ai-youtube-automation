"""Logging setup: rich console output plus an optional per-video file log."""

from __future__ import annotations

import logging
from pathlib import Path

from rich.logging import RichHandler

FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with a rich console handler. Call once at CLI start."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


def add_file_handler(workspace_dir: Path) -> logging.Handler:
    """Also write logs into the video workspace so each run keeps its own log."""
    handler = logging.FileHandler(workspace_dir / "pipeline.log")
    handler.setFormatter(logging.Formatter(FORMAT))
    logging.getLogger().addHandler(handler)
    return handler


def remove_handler(handler: logging.Handler) -> None:
    logging.getLogger().removeHandler(handler)
    handler.close()
