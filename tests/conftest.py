import json
from pathlib import Path
from typing import Any

import pytest

from yt_factory.config import Secrets, Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    prompts_dir = Path(__file__).resolve().parent.parent / "config" / "prompts"
    return Settings.model_validate(
        {
            "channel": {
                "name": "test",
                "lanes": ["how-tech-works"],
                "audience": "anyone",
                "tone": "clear",
            },
            "paths": {"videos_dir": tmp_path / "videos", "prompts_dir": prompts_dir},
            "video": {"target_minutes": 8, "resolution": [1920, 1080], "fps": 30},
            "providers": {
                "llm": "gemini",
                "llm_model": "gemini-flash-latest",
                "tts": "edge",
                "tts_voice": "en-US-AndrewNeural",
                "images": "pexels",
            },
            "automation": {"gates": ["script"], "upload_visibility": "private"},
        }
    )


@pytest.fixture
def secrets() -> Secrets:
    return Secrets(_env_file=None)


class FakeLLM:
    """Returns canned responses; records prompts for assertions."""

    def __init__(self, text: str = "fake text", data: Any = None) -> None:
        self.text = text
        self.data = data
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.text

    def generate_json(self, prompt: str) -> Any:
        self.prompts.append(prompt)
        return self.data


@pytest.fixture
def topic_brief() -> dict:
    return {
        "topic": "How GPS Works",
        "lane": "how-tech-works",
        "search_term": "how does gps work",
        "hook": "Satellites 20,000 km away know where you are within meters.",
        "angle": "clocks and time, not maps",
        "title_ideas": ["How GPS Actually Works"],
    }


def write_topic(ws: Any, brief: dict) -> None:
    ws.file("topic.json").write_text(json.dumps(brief))
