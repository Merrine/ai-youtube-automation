import json
import wave

import pytest

from yt_factory.config import Secrets, Settings
from yt_factory.stages.assembly import AssemblyStage, build_timeline
from yt_factory.stages.base import StageError
from yt_factory.workspace import Workspace

NARRATION = {
    "total_seconds": 3.0,
    "units": [
        {"index": 0, "section": "Hook", "cues": ["a"],
         "file": "narration/unit_000.wav", "seconds": 1.5},
        {"index": 1, "section": "Payoff", "cues": ["b"],
         "file": "narration/unit_001.wav", "seconds": 1.5},
    ],
}


def test_build_timeline_maps_units_to_own_clips() -> None:
    visuals = [
        {"id": "u000_0", "unit": 0, "file": "visuals/u000_0.mp4", "type": "video"},
        {"id": "u000_1", "unit": 0, "file": "visuals/u000_1.jpg", "type": "image"},
        {"id": "u001_0", "unit": 1, "file": "visuals/u001_0.mp4", "type": "video"},
    ]
    plans = build_timeline(NARRATION, visuals)
    assert [s["file"] for s in plans[0]["slots"]] == ["visuals/u000_0.mp4", "visuals/u000_1.jpg"]
    assert plans[1]["slots"] == [{"file": "visuals/u001_0.mp4", "type": "video"}]
    assert plans[0]["audio"] == "narration/unit_000.wav"


def test_build_timeline_fallback_for_bare_unit() -> None:
    visuals = [{"id": "u000_0", "unit": 0, "file": "visuals/u000_0.jpg", "type": "image"}]
    plans = build_timeline(NARRATION, visuals)
    assert plans[1]["slots"] == [{"file": "visuals/u000_0.jpg", "type": "image"}]


def test_build_timeline_empty_visuals_fails() -> None:
    with pytest.raises(StageError):
        build_timeline(NARRATION, [])


def _write_silent_wav(path: object, seconds: float) -> None:
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(8000)
        f.writeframes(b"\x00\x00" * int(8000 * seconds))


@pytest.mark.slow
def test_assembly_renders_mp4(settings: Settings, secrets: Secrets) -> None:
    from PIL import Image

    video_cfg = {"target_minutes": 1, "resolution": [320, 180], "fps": 10}
    small = Settings.model_validate(settings.model_dump() | {"video": video_cfg})
    ws = Workspace.create(small.paths.videos_dir, "Render Test", ["assembly"])
    narration_dir = ws.dir("narration")
    _write_silent_wav(narration_dir / "unit_000.wav", 1.5)
    _write_silent_wav(narration_dir / "unit_001.wav", 1.5)
    visuals_dir = ws.dir("visuals")
    Image.new("RGB", (640, 360), (200, 60, 60)).save(visuals_dir / "u000_0.jpg")
    Image.new("RGB", (640, 360), (60, 60, 200)).save(visuals_dir / "u001_0.jpg")
    ws.file("narration.json").write_text(json.dumps(NARRATION))
    ws.file("visuals.json").write_text(
        json.dumps([
            {"id": "u000_0", "unit": 0, "file": "visuals/u000_0.jpg", "type": "image"},
            {"id": "u001_0", "unit": 1, "file": "visuals/u001_0.jpg", "type": "image"},
        ])
    )
    AssemblyStage().run(ws, small, secrets)
    out = ws.file("video.mp4")
    assert out.exists() and out.stat().st_size > 1_000
