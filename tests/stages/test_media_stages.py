import json
from pathlib import Path

import pytest

from tests.conftest import FakeLLM, write_topic
from yt_factory.config import Secrets, Settings
from yt_factory.stages.base import StageError
from yt_factory.stages.narration import NarrationStage
from yt_factory.stages.thumbnail import ThumbnailStage
from yt_factory.stages.visuals import VisualsStage
from yt_factory.workspace import Workspace

SCRIPT = """## Hook
Your phone talks to space.
[VISUAL: satellite orbiting earth]

## Payoff
Now you know.
[VISUAL: person smiling at phone]
"""


@pytest.fixture
def ws(settings: Settings) -> Workspace:
    w = Workspace.create(settings.paths.videos_dir, "How GPS Works", ["narration"])
    w.file("script.md").write_text(SCRIPT)
    return w


class FakeTTS:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def synthesize(self, text: str, out_file: Path) -> None:
        self.texts.append(text)
        out_file.write_bytes(b"fake-mp3")


class FakeImages:
    def fetch(self, query: str, out_file: Path) -> dict | None:
        out_file.write_bytes(b"fake-jpg")
        return {"url": "https://pexels.com/x", "photographer": "Test"}


def test_narration_stage(
    ws: Workspace, settings: Settings, secrets: Secrets, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("yt_factory.stages.narration._mp3_duration", lambda p: 12.5)
    tts = FakeTTS()
    NarrationStage(tts=tts).run(ws, settings, secrets)
    index = json.loads(ws.file("narration.json").read_text())
    assert index["total_seconds"] == 25.0
    assert len(index["sections"]) == 2
    assert (ws.path / index["sections"][0]["file"]).exists()
    assert "[VISUAL" not in tts.texts[0]


def test_narration_requires_script(settings: Settings, secrets: Secrets) -> None:
    ws = Workspace.create(settings.paths.videos_dir, "Empty", ["narration"])
    with pytest.raises(StageError, match="script.md missing"):
        NarrationStage(tts=FakeTTS()).run(ws, settings, secrets)


def test_visuals_stage(ws: Workspace, settings: Settings, secrets: Secrets) -> None:
    queries = [
        {"id": "00_0", "query": "satellite space"},
        {"id": "01_0", "query": "person smiling phone"},
    ]
    VisualsStage(llm=FakeLLM(data=queries), images=FakeImages()).run(ws, settings, secrets)
    index = json.loads(ws.file("visuals.json").read_text())
    assert len(index) == 2
    assert index[0]["query"] == "satellite space"
    assert (ws.path / index[0]["file"]).exists()


def test_thumbnail_stage(
    ws: Workspace, settings: Settings, secrets: Secrets, topic_brief: dict
) -> None:
    from PIL import Image

    write_topic(ws, topic_brief)
    visuals_dir = ws.dir("visuals")
    Image.new("RGB", (800, 600), (10, 80, 160)).save(visuals_dir / "00_0.jpg")
    ws.file("visuals.json").write_text(
        json.dumps([{"file": "visuals/00_0.jpg"}])
    )
    ThumbnailStage().run(ws, settings, secrets)
    thumb = Image.open(ws.file("thumbnail.png"))
    assert thumb.size == (1280, 720)


def test_thumbnail_without_visuals_uses_plain_background(
    ws: Workspace, settings: Settings, secrets: Secrets, topic_brief: dict
) -> None:
    write_topic(ws, topic_brief)
    ThumbnailStage().run(ws, settings, secrets)
    assert ws.file("thumbnail.png").exists()
