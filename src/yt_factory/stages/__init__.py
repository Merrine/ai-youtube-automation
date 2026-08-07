"""Pipeline stages, in execution order."""

from yt_factory.stages.base import Stage
from yt_factory.stages.metadata import MetadataStage
from yt_factory.stages.placeholders import (
    AssemblyStage,
    NarrationStage,
    ThumbnailStage,
    UploadStage,
    VisualsStage,
)
from yt_factory.stages.research import ResearchStage
from yt_factory.stages.script import ScriptStage
from yt_factory.stages.topic import TopicStage

ALL_STAGES: list[Stage] = [
    TopicStage(),
    ResearchStage(),
    ScriptStage(),
    NarrationStage(),
    VisualsStage(),
    AssemblyStage(),
    ThumbnailStage(),
    MetadataStage(),
    UploadStage(),
]

STAGE_NAMES: list[str] = [s.name for s in ALL_STAGES]

__all__ = ["ALL_STAGES", "STAGE_NAMES", "Stage"]
