"""Placeholder stages for phases not yet built (assembly, upload).

Each writes a small marker artifact so orchestration, gates, and resume
logic stay exercisable end to end. Replaced in Phases 4-5.
"""

from __future__ import annotations

import logging

from yt_factory.config import Secrets, Settings
from yt_factory.stages.base import Stage
from yt_factory.workspace import Workspace

log = logging.getLogger(__name__)


class _PlaceholderStage(Stage):
    """Writes a marker file named after the stage. Replace in later phases."""

    def run(self, ws: Workspace, settings: Settings, secrets: Secrets) -> None:
        log.info("stage '%s' running (placeholder)", self.name)
        ws.file(f".placeholder_{self.name}").write_text(
            f"placeholder output of stage '{self.name}'\n"
        )


class AssemblyStage(_PlaceholderStage):
    name = "assembly"


class UploadStage(_PlaceholderStage):
    name = "upload"
