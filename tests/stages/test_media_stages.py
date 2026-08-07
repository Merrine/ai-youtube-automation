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

NARRATION = {
    "total_seconds": 20.0,
    "units": [
        {"index": 0, "section": "Hook", "cues": ["satellite orbiting earth"],
         "file": "narration/unit_000.mp3", "seconds": 14.0},
        {"index": 1, "section": "Payoff", "cues": ["person smiling at phone"],
         "file": "narration/unit_001.mp3", "seconds": 6.0},
    ],
}


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


class FakeMedia:
    """Video for 'satellite' queries, photo otherwise. Tracks exclude sets."""

    def __init__(self) -> None:
        self.counter = 0
        self.excludes_seen: list[set[str]] = []

    def fetch_video(
        self, query: str, out_file: Path, exclude: set[str] | None = None
    ) -> dict | None:
        self.excludes_seen.append(set(exclude or set()))
        if "satellite" not in query:
            return None
        self.counter += 1
        out_file.write_bytes(b"fake-mp4")
        return {"media_id": f"video:{self.counter}", "url": "u", "photographer": "T"}

    def fetch_image(
        self, query: str, out_file: Path, exclude: set[str] | None = None
    ) -> dict | None:
        self.counter += 1
        out_file.write_bytes(b"fake-jpg")
        return {"media_id": f"photo:{self.counter}", "url": "u", "photographer": "T"}


def test_narration_stage_per_unit(
    ws: Workspace, settings: Settings, secrets: Secrets, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("yt_factory.stages.narration._mp3_duration", lambda p: 5.0)
    tts = FakeTTS()
    NarrationStage(tts=tts).run(ws, settings, secrets)
    index = json.loads(ws.file("narration.json").read_text())
    assert index["total_seconds"] == 10.0
    assert len(index["units"]) == 2
    assert index["units"][0]["cues"] == ["satellite orbiting earth"]
    assert "[VISUAL" not in tts.texts[0]


def test_narration_requires_script(settings: Settings, secrets: Secrets) -> None:
    ws = Workspace.create(settings.paths.videos_dir, "Empty", ["narration"])
    with pytest.raises(StageError, match="script.md missing"):
        NarrationStage(tts=FakeTTS()).run(ws, settings, secrets)


def test_visuals_fetches_per_unit_with_dedup(
    ws: Workspace, settings: Settings, secrets: Secrets
) -> None:
    ws.file("narration.json").write_text(json.dumps(NARRATION))
    # unit 0 is 14s -> ceil(14/6)=3 clips; unit 1 is 6s -> 1 clip
    queries = [
        {"unit": 0, "queries": ["satellite launch", "satellite dish", "satellite orbit"]},
        {"unit": 1, "queries": ["person smiling phone"]},
    ]
    media = FakeMedia()
    VisualsStage(llm=FakeLLM(data=queries), images=media).run(ws, settings, secrets)
    index = json.loads(ws.file("visuals.json").read_text())
    assert len(index) == 4
    assert [v["unit"] for v in index] == [0, 0, 0, 1]
    assert [v["type"] for v in index] == ["video", "video", "video", "image"]
    # dedup: later fetches must carry previously used ids
    assert media.excludes_seen[-1]  # non-empty exclude set by the last call
    assert len({v["attribution"]["media_id"] for v in index}) == 4


def test_visuals_requires_narration(
    ws: Workspace, settings: Settings, secrets: Secrets
) -> None:
    with pytest.raises(StageError, match="narration.json missing"):
        VisualsStage(llm=FakeLLM(data=[]), images=FakeMedia()).run(ws, settings, secrets)


def test_thumbnail_stage(
    ws: Workspace, settings: Settings, secrets: Secrets, topic_brief: dict
) -> None:
    from PIL import Image

    write_topic(ws, topic_brief)
    visuals_dir = ws.dir("visuals")
    Image.new("RGB", (800, 600), (10, 80, 160)).save(visuals_dir / "u000_0.jpg")
    ws.file("visuals.json").write_text(
        json.dumps([{"file": "visuals/u000_0.jpg", "type": "image"}])
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
