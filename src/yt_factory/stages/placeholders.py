"""Placeholder stages proving the pipeline skeleton end to end.

Each will be replaced by a real implementation in Phases 2-5.
Until then, each writes a small marker artifact so the orchestration,
manifest updates, gates, and resume logic can be exercised for real.
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


class TopicStage(_PlaceholderStage):
    name = "topic"


class ResearchStage(_PlaceholderStage):
    name = "research"


class ScriptStage(_PlaceholderStage):
    name = "script"


class NarrationStage(_PlaceholderStage):
    name = "narration"


class VisualsStage(_PlaceholderStage):
    name = "visuals"


class AssemblyStage(_PlaceholderStage):
    name = "assembly"


class ThumbnailStage(_PlaceholderStage):
    name = "thumbnail"


class MetadataStage(_PlaceholderStage):
    name = "metadata"


class UploadStage(_PlaceholderStage):
    name = "upload"
