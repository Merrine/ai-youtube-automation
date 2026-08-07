"""Research stage: produce a fact brief (research.md) from the topic brief."""

from __future__ import annotations

import json
import logging

from yt_factory.config import Secrets, Settings
from yt_factory.prompts import load_prompt
from yt_factory.providers.llm import LLMProvider, get_llm
from yt_factory.stages.base import Stage, StageError
from yt_factory.stages.topic import TOPIC_FILE
from yt_factory.workspace import Workspace

log = logging.getLogger(__name__)

RESEARCH_FILE = "research.md"


class ResearchStage(Stage):
    name = "research"

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm

    def run(self, ws: Workspace, settings: Settings, secrets: Secrets) -> None:
        topic_path = ws.file(TOPIC_FILE)
        if not topic_path.exists():
            raise StageError("topic.json missing — run the topic stage first")
        brief = json.loads(topic_path.read_text())
        llm = self._llm or get_llm(settings, secrets)
        prompt = load_prompt(
            settings,
            "research",
            topic=brief["topic"],
            angle=brief["angle"],
            hook=brief["hook"],
            audience=settings.channel.audience,
        )
        research = llm.generate(prompt)
        ws.file(RESEARCH_FILE).write_text(research)
        log.info("research brief written (%d chars)", len(research))
