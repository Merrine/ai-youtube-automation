"""Per-video workspace: a folder on disk holding every artifact for one video.

The manifest.json inside it records the status of each pipeline stage,
which is what makes the pipeline resumable and individually re-runnable.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

MANIFEST_FILE = "manifest.json"


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    AWAITING_REVIEW = "awaiting_review"


class StageRecord(BaseModel):
    status: StageStatus = StageStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


class Manifest(BaseModel):
    video_id: str
    topic: str | None = None
    created_at: datetime
    stages: dict[str, StageRecord] = Field(default_factory=dict)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60]


class Workspace:
    """Wraps one video folder and its manifest."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @property
    def video_id(self) -> str:
        return self.path.name

    # -- creation / loading ------------------------------------------------

    @classmethod
    def create(cls, videos_dir: Path, topic: str, stage_names: list[str]) -> Workspace:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        path = videos_dir / f"{today}_{slugify(topic)}"
        if path.exists():
            raise FileExistsError(f"Workspace already exists: {path}")
        path.mkdir(parents=True)
        ws = cls(path)
        manifest = Manifest(
            video_id=ws.video_id,
            topic=topic,
            created_at=datetime.now(UTC),
            stages={name: StageRecord() for name in stage_names},
        )
        ws.save_manifest(manifest)
        return ws

    @classmethod
    def load(cls, videos_dir: Path, video_id: str) -> Workspace:
        path = videos_dir / video_id
        if not (path / MANIFEST_FILE).exists():
            raise FileNotFoundError(f"No workspace named '{video_id}' in {videos_dir}")
        return cls(path)

    @classmethod
    def list_all(cls, videos_dir: Path) -> list[Workspace]:
        if not videos_dir.exists():
            return []
        return [
            cls(p)
            for p in sorted(videos_dir.iterdir())
            if (p / MANIFEST_FILE).exists()
        ]

    # -- manifest ----------------------------------------------------------

    def manifest(self) -> Manifest:
        raw = (self.path / MANIFEST_FILE).read_text()
        return Manifest.model_validate_json(raw)

    def save_manifest(self, manifest: Manifest) -> None:
        (self.path / MANIFEST_FILE).write_text(manifest.model_dump_json(indent=2))

    def update_stage(self, name: str, **changes: object) -> None:
        manifest = self.manifest()
        record = manifest.stages.get(name, StageRecord())
        manifest.stages[name] = record.model_copy(update=changes)
        self.save_manifest(manifest)

    # -- artifact paths ----------------------------------------------------

    def file(self, name: str) -> Path:
        return self.path / name

    def dir(self, name: str) -> Path:
        d = self.path / name
        d.mkdir(exist_ok=True)
        return d
