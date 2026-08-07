"""Narration stage: synthesize per-section audio (narration/*.mp3 + narration.json)."""

from __future__ import annotations

import json
import logging

from yt_factory.config import Secrets, Settings
from yt_factory.providers.tts import TTSProvider, get_tts
from yt_factory.script_parse import parse_script
from yt_factory.stages.base import Stage, StageError
from yt_factory.stages.script import SCRIPT_FILE
from yt_factory.workspace import Workspace

log = logging.getLogger(__name__)

NARRATION_DIR = "narration"
NARRATION_FILE = "narration.json"


def _mp3_duration(path: object) -> float:
    from mutagen.mp3 import MP3

    return float(MP3(path).info.length)


class NarrationStage(Stage):
    name = "narration"

    def __init__(self, tts: TTSProvider | None = None) -> None:
        self._tts = tts

    def run(self, ws: Workspace, settings: Settings, secrets: Secrets) -> None:
        script_path = ws.file(SCRIPT_FILE)
        if not script_path.exists():
            raise StageError("script.md missing — run the script stage first")
        sections = parse_script(script_path.read_text())
        if not sections:
            raise StageError("script.md has no sections to narrate")

        tts = self._tts or get_tts(settings, secrets)
        out_dir = ws.dir(NARRATION_DIR)
        index = []
        for i, section in enumerate(sections):
            out_file = out_dir / f"section_{i:02d}.mp3"
            tts.synthesize(section.narration, out_file)
            duration = _mp3_duration(out_file)
            index.append(
                {
                    "section": section.title,
                    "file": f"{NARRATION_DIR}/{out_file.name}",
                    "seconds": round(duration, 2),
                }
            )
            log.info("narrated '%s' (%.1fs)", section.title, duration)

        total = sum(item["seconds"] for item in index)
        summary = {"total_seconds": round(total, 2), "sections": index}
        ws.file(NARRATION_FILE).write_text(json.dumps(summary, indent=2))
        log.info("narration complete: %d sections, %.1f minutes", len(index), total / 60)
