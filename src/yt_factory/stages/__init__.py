"""Pipeline stages, in execution order."""

from yt_factory.stages.base import Stage
from yt_factory.stages.placeholders import (
    AssemblyStage,
    MetadataStage,
    NarrationStage,
    ResearchStage,
    ScriptStage,
    ThumbnailStage,
    TopicStage,
    UploadStage,
    VisualsStage,
)

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
