from pathlib import Path

import pytest

from yt_factory import pipeline
from yt_factory.config import Secrets, Settings
from yt_factory.stages.base import Stage
from yt_factory.workspace import StageStatus, Workspace


class MarkerStage(Stage):
    def __init__(self, name: str) -> None:
        self.name = name

    def run(self, ws: Workspace, settings: Settings, secrets: Secrets) -> None:
        ws.file(f".ran_{self.name}").write_text("ok")


STAGES = [MarkerStage(n) for n in ["topic", "research", "script", "narration", "upload"]]
NAMES = [s.name for s in STAGES]


@pytest.fixture
def ws(settings: Settings) -> Workspace:
    return Workspace.create(settings.paths.videos_dir, "Gate Test", NAMES)


def test_run_pauses_at_gate(ws: Workspace, settings: Settings, secrets: Secrets) -> None:
    with pytest.raises(pipeline.GateReached) as exc:
        pipeline.run(ws, settings, secrets, stages=STAGES)
    assert exc.value.stage_name == "script"
    stages = ws.manifest().stages
    assert stages["script"].status == StageStatus.DONE
    assert stages["narration"].status == StageStatus.PENDING


def test_run_resumes_after_gate(ws: Workspace, settings: Settings, secrets: Secrets) -> None:
    with pytest.raises(pipeline.GateReached):
        pipeline.run(ws, settings, secrets, stages=STAGES)
    pipeline.run(ws, settings, secrets, stages=STAGES)
    assert all(r.status == StageStatus.DONE for r in ws.manifest().stages.values())


def test_ignore_gates_runs_to_end(ws: Workspace, settings: Settings, secrets: Secrets) -> None:
    pipeline.run(ws, settings, secrets, ignore_gates=True, stages=STAGES)
    assert all(r.status == StageStatus.DONE for r in ws.manifest().stages.values())


def test_until_stops_early(ws: Workspace, settings: Settings, secrets: Secrets) -> None:
    pipeline.run(ws, settings, secrets, until="research", ignore_gates=True, stages=STAGES)
    stages = ws.manifest().stages
    assert stages["research"].status == StageStatus.DONE
    assert stages["script"].status == StageStatus.PENDING


def test_failed_stage_recorded(
    ws: Workspace, settings: Settings, secrets: Secrets, tmp_path: Path
) -> None:
    class BoomStage(Stage):
        name = "topic"

        def run(self, ws: Workspace, settings: Settings, secrets: Secrets) -> None:
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        pipeline.run(ws, settings, secrets, stages=[BoomStage()])
    record = ws.manifest().stages["topic"]
    assert record.status == StageStatus.FAILED
    assert record.error == "boom"
