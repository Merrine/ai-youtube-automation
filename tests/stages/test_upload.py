import json
from pathlib import Path

import pytest

from yt_factory.config import Secrets, Settings
from yt_factory.stages.base import StageError
from yt_factory.stages.upload import UploadStage
from yt_factory.workspace import Workspace


class FakeUploader:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def upload(self, video_path: Path, title: str, description: str, tags: list[str],
               privacy: str, thumbnail_path: Path | None = None) -> str:
        self.calls.append({"title": title, "privacy": privacy, "thumb": thumbnail_path})
        return "abc123"


@pytest.fixture
def ws(settings: Settings) -> Workspace:
    w = Workspace.create(settings.paths.videos_dir, "Upload Test", ["upload"])
    w.file("video.mp4").write_bytes(b"fake")
    w.file("metadata.json").write_text(
        json.dumps({"title": "T", "description": "D", "tags": ["a"]})
    )
    return w


def test_upload_stage_records_result(ws: Workspace, settings: Settings, secrets: Secrets) -> None:
    uploader = FakeUploader()
    UploadStage(uploader=uploader).run(ws, settings, secrets)
    record = json.loads(ws.file("upload.json").read_text())
    assert record["video_id"] == "abc123"
    assert record["url"] == "https://youtu.be/abc123"
    assert record["visibility"] == "private"
    assert uploader.calls[0]["privacy"] == "private"


def test_upload_requires_video(settings: Settings, secrets: Secrets) -> None:
    ws = Workspace.create(settings.paths.videos_dir, "No Video", ["upload"])
    with pytest.raises(StageError, match="missing"):
        UploadStage(uploader=FakeUploader()).run(ws, settings, secrets)
