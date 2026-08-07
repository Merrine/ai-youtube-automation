"""Prompt templates: markdown files in config/prompts, simple {name} placeholders.

Plain str.replace (not str.format) so literal braces in JSON examples survive.
"""

from __future__ import annotations

from yt_factory.config import Settings


def load_prompt(settings: Settings, name: str, **values: object) -> str:
    path = settings.paths.prompts_dir / f"{name}.md"
    text = path.read_text()
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text
