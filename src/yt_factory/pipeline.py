"""Pipeline orchestration: run stages in order, honor review gates, resume."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from yt_factory.config import Secrets, Settings
from yt_factory.stages import ALL_STAGES, Stage
from yt_factory.workspace import StageStatus, Workspace

log = logging.getLogger(__name__)


class GateReached(Exception):
    """Pipeline paused at a human-review gate."""

    def __init__(self, stage_name: str) -> None:
        self.stage_name = stage_name
        super().__init__(f"paused for review after stage '{stage_name}'")


def next_pending_stage(ws: Workspace, stages: list[Stage] | None = None) -> Stage | None:
    """First stage that is not done yet, in pipeline order."""
    manifest = ws.manifest()
    for stage in stages or ALL_STAGES:
        record = manifest.stages.get(stage.name)
        if record is None or record.status != StageStatus.DONE:
            return stage
    return None


def run_stage(stage: Stage, ws: Workspace, settings: Settings, secrets: Secrets) -> None:
    """Run one stage, recording status transitions in the manifest."""
    ws.update_stage(
        stage.name, status=StageStatus.RUNNING, started_at=datetime.now(UTC), error=None
    )
    try:
        stage.run(ws, settings, secrets)
    except Exception as exc:
        ws.update_stage(
            stage.name, status=StageStatus.FAILED, finished_at=datetime.now(UTC), error=str(exc)
        )
        log.exception("stage '%s' failed", stage.name)
        raise
    ws.update_stage(stage.name, status=StageStatus.DONE, finished_at=datetime.now(UTC))
    log.info("stage '%s' done", stage.name)


def run(
    ws: Workspace,
    settings: Settings,
    secrets: Secrets,
    until: str | None = None,
    ignore_gates: bool = False,
    stages: list[Stage] | None = None,
) -> None:
    """Run pending stages in order.

    Stops when: all stages done, `until` stage completes, or a review gate
    (from settings.automation.gates) is hit — whichever comes first.
    Raises GateReached on a gate so the CLI can explain how to continue.
    """
    gates = set() if ignore_gates else set(settings.automation.gates)
    while (stage := next_pending_stage(ws, stages)) is not None:
        run_stage(stage, ws, settings, secrets)
        if stage.name == until:
            return
        if stage.name in gates:
            raise GateReached(stage.name)
