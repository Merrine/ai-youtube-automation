"""Stage contract: every pipeline step implements this interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from yt_factory.config import Secrets, Settings
from yt_factory.workspace import Workspace


class StageError(Exception):
    """Raised by a stage when it cannot complete its work."""


class Stage(ABC):
    """One step of the pipeline.

    A stage reads its inputs from the workspace, does its work, and writes
    its outputs back to the workspace. It must be safe to re-run: overwrite
    previous outputs rather than failing on their existence.
    """

    name: str

    @abstractmethod
    def run(self, ws: Workspace, settings: Settings, secrets: Secrets) -> None: ...
