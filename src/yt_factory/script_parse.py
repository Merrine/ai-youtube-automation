"""Parse script.md into narration units: one paragraph + its visual cue(s).

The script format (produced by the script stage prompt):
  ## Section Name
  narration paragraph...
  [VISUAL: what should be on screen]
  more narration...
  [VISUAL: ...]

A unit is the text between visual cues; the cue that follows the text
belongs to it. This 1:1 pairing is what lets the assembly stage show
each visual exactly while its paragraph is spoken.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

VISUAL_RE = re.compile(r"^\[VISUAL:\s*(.+?)\]\s*$", re.IGNORECASE)


@dataclass
class Unit:
    section: str
    text: str
    cues: list[str] = field(default_factory=list)


def parse_units(script_md: str) -> list[Unit]:
    units: list[Unit] = []
    section = ""
    text_lines: list[str] = []

    def close(cue: str | None) -> None:
        text = "\n".join(text_lines).strip()
        text_lines.clear()
        if text:
            units.append(Unit(section, text, [cue] if cue else []))
        elif cue:
            # cue with no new text: extra visual for the previous unit
            if units:
                units[-1].cues.append(cue)

    for line in script_md.splitlines():
        if line.startswith("## "):
            close(None)
            section = line[3:].strip()
            continue
        match = VISUAL_RE.match(line.strip())
        if match:
            close(match.group(1).strip())
        else:
            text_lines.append(line)
    close(None)
    return units
