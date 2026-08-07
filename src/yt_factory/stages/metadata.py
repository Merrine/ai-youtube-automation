"""Metadata stage: title, description, tags (metadata.json) from the script."""

from __future__ import annotations

import json
import logging

from yt_factory.config import Secrets, Settings
from yt_factory.prompts import load_prompt
from yt_factory.providers.llm import LLMProvider, get_llm
from yt_factory.stages.base import Stage, StageError
from yt_factory.stages.script import SCRIPT_FILE
from yt_factory.stages.topic import TOPIC_FILE
from yt_factory.workspace import Workspace

log = logging.getLogger(__name__)

METADATA_FILE = "metadata.json"


class MetadataStage(Stage):
    name = "metadata"

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm

    def run(self, ws: Workspace, settings: Settings, secrets: Secrets) -> None:
        topic_path = ws.file(TOPIC_FILE)
        script_path = ws.file(SCRIPT_FILE)
        if not topic_path.exists() or not script_path.exists():
            raise StageError("topic.json or script.md missing — run earlier stages first")
        brief = json.loads(topic_path.read_text())
        llm = self._llm or get_llm(settings, secrets)
        prompt = load_prompt(
            settings,
            "metadata",
            topic=brief["topic"],
            search_term=brief["search_term"],
            title_ideas=", ".join(brief.get("title_ideas", [])),
            script=script_path.read_text(),
        )
        metadata = llm.generate_json(prompt)
        for field in ("title", "description", "tags"):
            if field not in metadata:
                raise StageError(f"metadata missing field '{field}'")
        ws.file(METADATA_FILE).write_text(json.dumps(metadata, indent=2))
        log.info("metadata written: %s", metadata["title"])
