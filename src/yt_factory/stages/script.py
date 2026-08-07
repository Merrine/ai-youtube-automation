"""Script stage: write the full narration script (script.md)."""

from __future__ import annotations

import json
import logging

from yt_factory.config import Secrets, Settings
from yt_factory.prompts import load_prompt
from yt_factory.providers.llm import LLMProvider, get_llm
from yt_factory.stages.base import Stage, StageError
from yt_factory.stages.research import RESEARCH_FILE
from yt_factory.stages.topic import TOPIC_FILE
from yt_factory.workspace import Workspace

log = logging.getLogger(__name__)

SCRIPT_FILE = "script.md"
WORDS_PER_MINUTE = 150


class ScriptStage(Stage):
    name = "script"

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm

    def run(self, ws: Workspace, settings: Settings, secrets: Secrets) -> None:
        topic_path = ws.file(TOPIC_FILE)
        research_path = ws.file(RESEARCH_FILE)
        if not topic_path.exists() or not research_path.exists():
            raise StageError("topic.json or research.md missing — run earlier stages first")
        brief = json.loads(topic_path.read_text())
        llm = self._llm or get_llm(settings, secrets)
        prompt = load_prompt(
            settings,
            "script",
            topic=brief["topic"],
            hook=brief["hook"],
            angle=brief["angle"],
            audience=settings.channel.audience,
            tone=settings.channel.tone,
            target_minutes=settings.video.target_minutes,
            words=settings.video.target_minutes * WORDS_PER_MINUTE,
            research=research_path.read_text(),
        )
        script = llm.generate(prompt)
        ws.file(SCRIPT_FILE).write_text(script)
        words = len(script.split())
        log.info("script written (~%d words, target %d)", words,
                 settings.video.target_minutes * WORDS_PER_MINUTE)
