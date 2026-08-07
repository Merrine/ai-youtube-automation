"""Parse script.md into sections: narration text + visual cues.

The script format (produced by the script stage prompt):
  ## Section Name
  narration paragraph...
  [VISUAL: what should be on screen]
  more narration...
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

VISUAL_RE = re.compile(r"^\[VISUAL:\s*(.+?)\]\s*$", re.IGNORECASE)


@dataclass
class Section:
    title: str
    narration: str = ""
    visuals: list[str] = field(default_factory=list)


def parse_script(script_md: str) -> list[Section]:
    sections: list[Section] = []
    current: Section | None = None
    narration_lines: list[str] = []

    def flush() -> None:
        if current is not None:
            current.narration = "\n".join(narration_lines).strip()
            sections.append(current)

    for line in script_md.splitlines():
        if line.startswith("## "):
            flush()
            current = Section(title=line[3:].strip())
            narration_lines = []
            continue
        if current is None:
            continue
        match = VISUAL_RE.match(line.strip())
        if match:
            current.visuals.append(match.group(1).strip())
        else:
            narration_lines.append(line)
    flush()
    return [s for s in sections if s.narration]
