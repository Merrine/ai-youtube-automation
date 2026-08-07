import json

import pytest

from tests.conftest import FakeLLM, write_topic
from yt_factory.config import Secrets, Settings
from yt_factory.stages.base import StageError
from yt_factory.stages.metadata import MetadataStage
from yt_factory.stages.research import ResearchStage
from yt_factory.stages.script import ScriptStage
from yt_factory.stages.topic import TopicStage, generate_candidates
from yt_factory.workspace import Workspace


@pytest.fixture
def ws(settings: Settings) -> Workspace:
    return Workspace.create(settings.paths.videos_dir, "How GPS Works", ["topic"])


def test_topic_stage_writes_brief(
    ws: Workspace, settings: Settings, secrets: Secrets, topic_brief: dict
) -> None:
    stage = TopicStage(llm=FakeLLM(data=topic_brief))
    stage.run(ws, settings, secrets)
    saved = json.loads(ws.file("topic.json").read_text())
    assert saved["topic"] == "How GPS Works"


def test_topic_stage_rejects_incomplete_brief(
    ws: Workspace, settings: Settings, secrets: Secrets
) -> None:
    stage = TopicStage(llm=FakeLLM(data={"topic": "x"}))
    with pytest.raises(StageError, match="missing field"):
        stage.run(ws, settings, secrets)


def test_generate_candidates_dedups_history(settings: Settings, secrets: Secrets) -> None:
    data = [
        {"topic": "How GPS Works", "score": 9},
        {"topic": "Why Nokia Failed", "score": 8},
    ]
    result = generate_candidates(settings, secrets, ["How GPS Works"], llm=FakeLLM(data=data))
    assert [c["topic"] for c in result] == ["Why Nokia Failed"]


def test_research_stage(
    ws: Workspace, settings: Settings, secrets: Secrets, topic_brief: dict
) -> None:
    write_topic(ws, topic_brief)
    llm = FakeLLM(text="## Key facts\n- fact one")
    ResearchStage(llm=llm).run(ws, settings, secrets)
    assert "fact one" in ws.file("research.md").read_text()
    assert "How GPS Works" in llm.prompts[0]


def test_research_requires_topic(ws: Workspace, settings: Settings, secrets: Secrets) -> None:
    with pytest.raises(StageError, match="topic.json missing"):
        ResearchStage(llm=FakeLLM()).run(ws, settings, secrets)


def test_script_stage(
    ws: Workspace, settings: Settings, secrets: Secrets, topic_brief: dict
) -> None:
    write_topic(ws, topic_brief)
    ws.file("research.md").write_text("## Key facts\n- satellites carry atomic clocks")
    llm = FakeLLM(text="## Hook\nYour phone talks to space.")
    ScriptStage(llm=llm).run(ws, settings, secrets)
    assert "Hook" in ws.file("script.md").read_text()
    assert "atomic clocks" in llm.prompts[0]  # research fed into prompt
    assert "1200" in llm.prompts[0]  # 8 min * 150 wpm word target


def test_metadata_stage(
    ws: Workspace, settings: Settings, secrets: Secrets, topic_brief: dict
) -> None:
    write_topic(ws, topic_brief)
    ws.file("script.md").write_text("## Hook\ntext")
    data = {"title": "How GPS Actually Works", "description": "d", "tags": ["gps"]}
    MetadataStage(llm=FakeLLM(data=data)).run(ws, settings, secrets)
    saved = json.loads(ws.file("metadata.json").read_text())
    assert saved["title"] == "How GPS Actually Works"


def test_metadata_rejects_missing_fields(
    ws: Workspace, settings: Settings, secrets: Secrets, topic_brief: dict
) -> None:
    write_topic(ws, topic_brief)
    ws.file("script.md").write_text("s")
    with pytest.raises(StageError, match="missing field"):
        MetadataStage(llm=FakeLLM(data={"title": "t"})).run(ws, settings, secrets)
