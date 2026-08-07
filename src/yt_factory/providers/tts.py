"""Text-to-speech provider abstraction."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Protocol

from yt_factory.config import Secrets, Settings


class TTSError(Exception):
    """TTS synthesis failed."""


class TTSProvider(Protocol):
    def synthesize(self, text: str, out_file: Path) -> None:
        """Render `text` as speech into `out_file` (mp3)."""
        ...


class EdgeTTSProvider:
    """Microsoft Edge neural voices via edge-tts. Free, no API key."""

    def __init__(self, voice: str) -> None:
        self._voice = voice

    def synthesize(self, text: str, out_file: Path) -> None:
        import edge_tts

        async def _run() -> None:
            communicate = edge_tts.Communicate(text, self._voice)
            await communicate.save(str(out_file))

        asyncio.run(_run())
        if not out_file.exists() or out_file.stat().st_size == 0:
            raise TTSError(f"edge-tts produced no audio for {out_file.name}")


def get_tts(settings: Settings, secrets: Secrets) -> TTSProvider:
    name = settings.providers.tts
    if name == "edge":
        return EdgeTTSProvider(settings.providers.tts_voice)
    raise TTSError(f"Unknown TTS provider '{name}' (supported: edge)")
