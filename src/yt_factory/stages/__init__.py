"""Pipeline stages, in execution order."""

from yt_factory.stages.base import Stage
from yt_factory.stages.metadata import MetadataStage
from yt_factory.stages.narration import NarrationStage
from yt_factory.stages.placeholders import AssemblyStage, UploadStage
from yt_factory.stages.research import ResearchStage
from yt_factory.stages.script import ScriptStage
from yt_factory.stages.thumbnail import ThumbnailStage
from yt_factory.stages.topic import TopicStage
from yt_factory.stages.visuals import VisualsStage

ALL_STAGES: list[Stage] = [
    TopicStage(),
    ResearchStage(),
    ScriptStage(),
    MetadataStage(),
    NarrationStage(),
    VisualsStage(),
    AssemblyStage(),
    ThumbnailStage(),
    UploadStage(),
]

STAGE_NAMES: list[str] = [s.name for s in ALL_STAGES]

__all__ = ["ALL_STAGES", "STAGE_NAMES", "Stage"]
