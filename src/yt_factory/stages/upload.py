"""Upload stage: publish video.mp4 + metadata + thumbnail to YouTube."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from yt_factory.config import Secrets, Settings
from yt_factory.providers.youtube import YouTubeUploader, get_uploader
from yt_factory.stages.assembly import VIDEO_FILE
from yt_factory.stages.base import Stage, StageError
from yt_factory.stages.metadata import METADATA_FILE
from yt_factory.stages.thumbnail import THUMBNAIL_FILE
from yt_factory.workspace import Workspace

log = logging.getLogger(__name__)

UPLOAD_FILE = "upload.json"


class UploadStage(Stage):
    name = "upload"

    def __init__(self, uploader: YouTubeUploader | None = None) -> None:
        self._uploader = uploader

    def run(self, ws: Workspace, settings: Settings, secrets: Secrets) -> None:
        video_path = ws.file(VIDEO_FILE)
        metadata_path = ws.file(METADATA_FILE)
        if not video_path.exists() or not metadata_path.exists():
            raise StageError("video.mp4 or metadata.json missing — run earlier stages first")
        metadata = json.loads(metadata_path.read_text())

        uploader = self._uploader or get_uploader(secrets)
        thumbnail = ws.file(THUMBNAIL_FILE)
        video_id = uploader.upload(
            video_path=video_path,
            title=metadata["title"],
            description=metadata["description"],
            tags=metadata.get("tags", []),
            privacy=settings.automation.upload_visibility,
            thumbnail_path=thumbnail if thumbnail.exists() else None,
        )
        record = {
            "video_id": video_id,
            "url": f"https://youtu.be/{video_id}",
            "visibility": settings.automation.upload_visibility,
            "uploaded_at": datetime.now(UTC).isoformat(),
        }
        ws.file(UPLOAD_FILE).write_text(json.dumps(record, indent=2))
        log.info("upload recorded: %s", record["url"])
