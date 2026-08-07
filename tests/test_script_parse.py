from yt_factory.script_parse import parse_units

SCRIPT = """## Hook

Your phone talks to space.

[VISUAL: satellite orbiting earth]

And it does it constantly.

## The Clocks

Atomic clocks keep the time.

[VISUAL: atomic clock closeup]
[VISUAL: control room with screens]

They drift a tiny bit every day.
"""


def test_units_pair_text_with_following_cue() -> None:
    units = parse_units(SCRIPT)
    assert units[0].text == "Your phone talks to space."
    assert units[0].cues == ["satellite orbiting earth"]
    assert units[0].section == "Hook"


def test_trailing_text_without_cue_becomes_unit() -> None:
    units = parse_units(SCRIPT)
    assert units[1].text == "And it does it constantly."
    assert units[1].cues == []


def test_consecutive_cues_attach_to_same_unit() -> None:
    units = parse_units(SCRIPT)
    clocks = units[2]
    assert clocks.section == "The Clocks"
    assert clocks.cues == ["atomic clock closeup", "control room with screens"]
    assert units[3].text == "They drift a tiny bit every day."


def test_visual_lines_never_in_text() -> None:
    for unit in parse_units(SCRIPT):
        assert "[VISUAL" not in unit.text
