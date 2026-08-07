from yt_factory.script_parse import parse_script

SCRIPT = """## Hook

Your phone talks to space.

[VISUAL: satellite orbiting earth]

And it does it constantly.

## The Clocks

Atomic clocks keep the time.

[VISUAL: atomic clock closeup]
[VISUAL: control room with screens]
"""


def test_parse_sections() -> None:
    sections = parse_script(SCRIPT)
    assert [s.title for s in sections] == ["Hook", "The Clocks"]


def test_narration_excludes_visual_cues() -> None:
    hook = parse_script(SCRIPT)[0]
    assert "satellite orbiting" not in hook.narration
    assert "Your phone talks to space." in hook.narration
    assert "And it does it constantly." in hook.narration


def test_visual_cues_collected() -> None:
    clocks = parse_script(SCRIPT)[1]
    assert clocks.visuals == ["atomic clock closeup", "control room with screens"]


def test_empty_sections_dropped() -> None:
    assert parse_script("## Empty\n\n## Real\ntext") == parse_script("## Real\ntext")
