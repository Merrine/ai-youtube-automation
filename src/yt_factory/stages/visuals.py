"""Visuals stage: turn [VISUAL:] cues into stock images (visuals/*.jpg + visuals.json).

One LLM call converts all cues into short stock-photo search queries,
then each query is fetched from the image provider.
"""

from __future__ import annotations

import json
import logging

from yt_factory.config import Secrets, Settings
from yt_factory.prompts import load_prompt
from yt_factory.providers.images import ImageProvider, get_images
from yt_factory.providers.llm import LLMProvider, get_llm
from yt_factory.script_parse import parse_script
from yt_factory.stages.base import Stage, StageError
from yt_factory.stages.script import SCRIPT_FILE
from yt_factory.workspace import Workspace

log = logging.getLogger(__name__)

VISUALS_DIR = "visuals"
VISUALS_FILE = "visuals.json"


class VisualsStage(Stage):
    name = "visuals"

    def __init__(
        self, llm: LLMProvider | None = None, images: ImageProvider | None = None
    ) -> None:
        self._llm = llm
        self._images = images

    def run(self, ws: Workspace, settings: Settings, secrets: Secrets) -> None:
        script_path = ws.file(SCRIPT_FILE)
        if not script_path.exists():
            raise StageError("script.md missing — run the script stage first")
        sections = parse_script(script_path.read_text())
        cues = [
            {"id": f"{i:02d}_{j}", "section": s.title, "cue": cue}
            for i, s in enumerate(sections)
            for j, cue in enumerate(s.visuals)
        ]
        if not cues:
            raise StageError("script.md has no [VISUAL:] cues")

        llm = self._llm or get_llm(settings, secrets)
        prompt = load_prompt(
            settings,
            "visual_queries",
            cues=json.dumps([{"id": c["id"], "cue": c["cue"]} for c in cues], indent=1),
        )
        queries = {q["id"]: q["query"] for q in llm.generate_json(prompt)}

        images = self._images or get_images(settings, secrets)
        out_dir = ws.dir(VISUALS_DIR)
        index, missing = [], 0
        for c in cues:
            query = queries.get(c["id"], c["cue"][:60])
            out_file = out_dir / f"{c['id']}.jpg"
            attribution = images.fetch(query, out_file)
            if attribution is None:
                missing += 1
                continue
            index.append({**c, "query": query, "file": f"{VISUALS_DIR}/{out_file.name}",
                          "attribution": attribution})
        if not index:
            raise StageError("no visuals could be fetched")
        ws.file(VISUALS_FILE).write_text(json.dumps(index, indent=2))
        log.info("visuals complete: %d fetched, %d without result", len(index), missing)
