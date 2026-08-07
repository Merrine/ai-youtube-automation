"""Visuals stage: fetch unique footage per narration unit (visuals/* + visuals.json).

Reads narration.json for unit durations, computes how many clips each
unit needs (respecting video.max_visual_seconds), asks the LLM for that
many distinct search queries per unit, and fetches videos (photos as
fallback) with global dedup so no clip appears twice in the video.
"""

from __future__ import annotations

import json
import logging
import math

from yt_factory.config import Secrets, Settings
from yt_factory.prompts import load_prompt
from yt_factory.providers.images import MediaProvider, get_images
from yt_factory.providers.llm import LLMProvider, get_llm
from yt_factory.stages.base import Stage, StageError
from yt_factory.stages.narration import NARRATION_FILE
from yt_factory.workspace import Workspace

log = logging.getLogger(__name__)

VISUALS_DIR = "visuals"
VISUALS_FILE = "visuals.json"


class VisualsStage(Stage):
    name = "visuals"

    def __init__(
        self, llm: LLMProvider | None = None, images: MediaProvider | None = None
    ) -> None:
        self._llm = llm
        self._images = images

    def run(self, ws: Workspace, settings: Settings, secrets: Secrets) -> None:
        narration_path = ws.file(NARRATION_FILE)
        if not narration_path.exists():
            raise StageError("narration.json missing — run the narration stage first")
        units = json.loads(narration_path.read_text())["units"]

        max_seconds = settings.video.max_visual_seconds
        requests_spec = []
        for unit in units:
            n_clips = max(1, math.ceil(unit["seconds"] / max_seconds))
            requests_spec.append(
                {"unit": unit["index"], "cues": unit["cues"] or [unit["section"]], "n": n_clips}
            )

        llm = self._llm or get_llm(settings, secrets)
        prompt = load_prompt(settings, "visual_queries", units=json.dumps(requests_spec, indent=1))
        queries_by_unit: dict[int, list[str]] = {
            item["unit"]: item["queries"] for item in llm.generate_json(prompt)
        }

        media = self._images or get_images(settings, secrets)
        out_dir = ws.dir(VISUALS_DIR)
        used_ids: set[str] = set()
        index, missing, n_videos = [], 0, 0
        for spec in requests_spec:
            unit_idx = spec["unit"]
            queries = queries_by_unit.get(unit_idx) or [c[:60] for c in spec["cues"]]
            for slot in range(spec["n"]):
                query = queries[slot % len(queries)]
                entry_id = f"u{unit_idx:03d}_{slot}"
                video_file = out_dir / f"{entry_id}.mp4"
                attribution = media.fetch_video(query, video_file, exclude=used_ids)
                if attribution is not None:
                    kind, out_file = "video", video_file
                    n_videos += 1
                else:
                    out_file = out_dir / f"{entry_id}.jpg"
                    attribution = media.fetch_image(query, out_file, exclude=used_ids)
                    kind = "image"
                if attribution is None:
                    missing += 1
                    continue
                used_ids.add(attribution["media_id"])
                index.append(
                    {"id": entry_id, "unit": unit_idx, "query": query, "type": kind,
                     "file": f"{VISUALS_DIR}/{out_file.name}", "attribution": attribution}
                )
        if not index:
            raise StageError("no visuals could be fetched")
        ws.file(VISUALS_FILE).write_text(json.dumps(index, indent=2))
        log.info("visuals complete: %d fetched (%d videos, %d photos), %d slots unfilled",
                 len(index), n_videos, len(index) - n_videos, missing)
