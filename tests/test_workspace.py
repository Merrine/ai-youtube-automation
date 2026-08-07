from pathlib import Path

import pytest

from yt_factory.workspace import StageStatus, Workspace, slugify


def test_slugify() -> None:
    assert slugify("How Wi-Fi Works!") == "how-wi-fi-works"


def test_create_and_load(tmp_path: Path) -> None:
    ws = Workspace.create(tmp_path, "How GPS Works", ["topic", "script"])
    manifest = ws.manifest()
    assert manifest.topic == "How GPS Works"
    assert set(manifest.stages) == {"topic", "script"}
    assert all(r.status == StageStatus.PENDING for r in manifest.stages.values())

    loaded = Workspace.load(tmp_path, ws.video_id)
    assert loaded.manifest().topic == "How GPS Works"


def test_create_duplicate_fails(tmp_path: Path) -> None:
    Workspace.create(tmp_path, "Same Topic", ["topic"])
    with pytest.raises(FileExistsError):
        Workspace.create(tmp_path, "Same Topic", ["topic"])


def test_update_stage(tmp_path: Path) -> None:
    ws = Workspace.create(tmp_path, "Topic", ["topic"])
    ws.update_stage("topic", status=StageStatus.DONE)
    assert ws.manifest().stages["topic"].status == StageStatus.DONE


def test_list_all(tmp_path: Path) -> None:
    assert Workspace.list_all(tmp_path) == []
    Workspace.create(tmp_path, "A", ["topic"])
    Workspace.create(tmp_path, "B", ["topic"])
    assert len(Workspace.list_all(tmp_path)) == 2
