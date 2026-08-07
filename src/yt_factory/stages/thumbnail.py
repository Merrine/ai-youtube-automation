"""Thumbnail stage: compose thumbnail.png from the best visual + big title text."""

from __future__ import annotations

import json
import logging
import textwrap
from pathlib import Path

from yt_factory.config import Secrets, Settings
from yt_factory.stages.base import Stage, StageError
from yt_factory.stages.metadata import METADATA_FILE
from yt_factory.stages.topic import TOPIC_FILE
from yt_factory.stages.visuals import VISUALS_FILE
from yt_factory.workspace import Workspace

log = logging.getLogger(__name__)

THUMBNAIL_FILE = "thumbnail.png"
SIZE = (1280, 720)
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _find_font() -> str:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return path
    raise StageError("no usable bold font found — add one to FONT_CANDIDATES")


class ThumbnailStage(Stage):
    name = "thumbnail"

    def run(self, ws: Workspace, settings: Settings, secrets: Secrets) -> None:
        from PIL import Image, ImageDraw, ImageEnhance, ImageFont

        title = self._pick_title(ws)
        background = self._pick_background(ws)

        if background is not None:
            img = Image.open(background).convert("RGB")
            img = img.resize(self._cover_size(img.size), Image.LANCZOS).crop((0, 0, *SIZE))
            img = ImageEnhance.Brightness(img).enhance(0.55)  # darken for text contrast
        else:
            img = Image.new("RGB", SIZE, (18, 18, 32))

        draw = ImageDraw.Draw(img)
        lines = textwrap.wrap(title.upper(), width=16)[:3]
        font_size = 110 if len(lines) <= 2 else 88
        font = ImageFont.truetype(_find_font(), font_size)
        line_height = font_size + 14
        y = SIZE[1] // 2 - (len(lines) * line_height) // 2
        for line in lines:
            draw.text((60, y), line, font=font, fill="white",
                      stroke_width=6, stroke_fill="black")
            y += line_height

        img.save(ws.file(THUMBNAIL_FILE))
        log.info("thumbnail written: %s", title)

    @staticmethod
    def _cover_size(original: tuple[int, int]) -> tuple[int, int]:
        """Scale so the image covers SIZE (crop the overflow)."""
        w, h = original
        scale = max(SIZE[0] / w, SIZE[1] / h)
        return (round(w * scale), round(h * scale))

    @staticmethod
    def _pick_title(ws: Workspace) -> str:
        metadata_path = ws.file(METADATA_FILE)
        if metadata_path.exists():
            return json.loads(metadata_path.read_text())["title"]
        topic_path = ws.file(TOPIC_FILE)
        if topic_path.exists():
            brief = json.loads(topic_path.read_text())
            if brief.get("title_ideas"):
                return brief["title_ideas"][0]
            return brief["topic"]
        manifest_topic = ws.manifest().topic
        if manifest_topic:
            return manifest_topic
        raise StageError("no title source found (metadata.json / topic.json / manifest)")

    @staticmethod
    def _pick_background(ws: Workspace) -> Path | None:
        visuals_path = ws.file(VISUALS_FILE)
        if not visuals_path.exists():
            return None
        index = json.loads(visuals_path.read_text())
        if not index:
            return None
        return ws.path / index[0]["file"]
