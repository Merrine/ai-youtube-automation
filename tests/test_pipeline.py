from pathlib import Path

import pytest

from yt_factory import pipeline
from yt_factory.config import Secrets, Settings
from yt_factory.stages import STAGE_NAMES
from yt_factory.workspace import StageStatus, Workspace


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings.model_validate(
        {
            "channel": {
                "name": "test",
                "lanes": ["how-tech-works"],
                "audience": "anyone",
                "tone": "clear",
            },
            "paths": {"videos_dir": tmp_path, "prompts_dir": tmp_path},
            "video": {"target_minutes": 8, "resolution": [1920, 1080], "fps": 30},
            "providers": {"llm": "claude", "tts": "local", "images": "pexels"},
            "automation": {"gates": ["script"], "upload_visibility": "private"},
        }
    )


@pytest.fixture
def secrets() -> Secrets:
    return Secrets(_env_file=None)


def test_run_pauses_at_gate(tmp_path: Path, settings: Settings, secrets: Secrets) -> None:
    ws = Workspace.create(tmp_path, "Gate Test", STAGE_NAMES)
    with pytest.raises(pipeline.GateReached) as exc:
        pipeline.run(ws, settings, secrets)
    assert exc.value.stage_name == "script"
    stages = ws.manifest().stages
    assert stages["script"].status == StageStatus.DONE
    assert stages["narration"].status == StageStatus.PENDING


def test_run_resumes_after_gate(tmp_path: Path, settings: Settings, secrets: Secrets) -> None:
    ws = Workspace.create(tmp_path, "Resume Test", STAGE_NAMES)
    with pytest.raises(pipeline.GateReached):
        pipeline.run(ws, settings, secrets)
    pipeline.run(ws, settings, secrets)  # only 'script' gate configured -> runs to end
    assert all(r.status == StageStatus.DONE for r in ws.manifest().stages.values())


def test_ignore_gates_runs_to_end(tmp_path: Path, settings: Settings, secrets: Secrets) -> None:
    ws = Workspace.create(tmp_path, "Auto Test", STAGE_NAMES)
    pipeline.run(ws, settings, secrets, ignore_gates=True)
    assert all(r.status == StageStatus.DONE for r in ws.manifest().stages.values())


def test_until_stops_early(tmp_path: Path, settings: Settings, secrets: Secrets) -> None:
    ws = Workspace.create(tmp_path, "Until Test", STAGE_NAMES)
    pipeline.run(ws, settings, secrets, until="research", ignore_gates=True)
    stages = ws.manifest().stages
    assert stages["research"].status == StageStatus.DONE
    assert stages["script"].status == StageStatus.PENDING
