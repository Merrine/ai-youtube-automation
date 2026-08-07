"""Topic stage: expand the chosen topic into a content brief (topic.json).

Also provides candidate generation used by `ytf new` when no topic is given.
"""

from __future__ import annotations

import json
import logging

from yt_factory.config import Secrets, Settings
from yt_factory.prompts import load_prompt
from yt_factory.providers.llm import LLMProvider, get_llm
from yt_factory.stages.base import Stage, StageError
from yt_factory.workspace import Workspace

log = logging.getLogger(__name__)

TOPIC_FILE = "topic.json"


def generate_candidates(
    settings: Settings, secrets: Secrets, history: list[str], llm: LLMProvider | None = None
) -> list[dict]:
    """Suggest ranked topic candidates that avoid already-made topics."""
    llm = llm or get_llm(settings, secrets)
    prompt = load_prompt(
        settings,
        "topic_candidates",
        lanes=", ".join(settings.channel.lanes),
        audience=settings.channel.audience,
        tone=settings.channel.tone,
        history="\n".join(f"- {t}" for t in history) or "(none yet)",
        target_minutes=settings.video.target_minutes,
    )
    candidates = llm.generate_json(prompt)
    if not isinstance(candidates, list) or not candidates:
        raise StageError("topic candidate generation returned no candidates")
    made = {t.lower() for t in history}
    fresh = [c for c in candidates if c.get("topic", "").lower() not in made]
    return sorted(fresh, key=lambda c: c.get("score", 0), reverse=True)


class TopicStage(Stage):
    name = "topic"

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm

    def run(self, ws: Workspace, settings: Settings, secrets: Secrets) -> None:
        topic = ws.manifest().topic
        if not topic:
            raise StageError("workspace has no topic in manifest")
        llm = self._llm or get_llm(settings, secrets)
        prompt = load_prompt(
            settings,
            "topic_expand",
            lanes=", ".join(settings.channel.lanes),
            audience=settings.channel.audience,
            topic=topic,
        )
        brief = llm.generate_json(prompt)
        for field in ("topic", "hook", "angle", "search_term", "title_ideas"):
            if field not in brief:
                raise StageError(f"topic brief missing field '{field}'")
        ws.file(TOPIC_FILE).write_text(json.dumps(brief, indent=2))
        log.info("topic brief written: %s", brief["topic"])
