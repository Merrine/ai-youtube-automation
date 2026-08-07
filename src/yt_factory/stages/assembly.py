"""Assembly stage: narration + visuals -> video.mp4.

Style: synced montage. Narration is per script unit (paragraph); each
unit's own footage plays exactly while its words are spoken. A unit's
time is split equally among its clips (stock video preferred, photos
with Ken Burns zoom as fallback). Video length locked to the audio.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from yt_factory.config import Secrets, Settings
from yt_factory.stages.base import Stage, StageError
from yt_factory.stages.narration import NARRATION_FILE
from yt_factory.stages.visuals import VISUALS_FILE
from yt_factory.workspace import Workspace

log = logging.getLogger(__name__)

VIDEO_FILE = "video.mp4"
ZOOM = 1.08  # end scale of the Ken Burns zoom per still image


def build_timeline(narration: dict, visuals: list[dict]) -> list[dict[str, Any]]:
    """Map each narration unit to its audio and its own visual slots.

    Units without any fetched visual borrow the previous unit's last
    clip (or the first overall) so the screen is never empty.
    """
    if not visuals:
        raise StageError("visuals.json is empty")
    plans: list[dict[str, Any]] = []
    fallback = {"file": visuals[0]["file"], "type": visuals[0].get("type", "image")}
    for unit in narration["units"]:
        media = [
            {"file": v["file"], "type": v.get("type", "image")}
            for v in visuals
            if v["unit"] == unit["index"]
        ]
        if not media:
            media = [fallback]
        plans.append({"audio": unit["file"], "seconds": unit["seconds"], "slots": media})
        fallback = media[-1]
    return plans


def _cover_frame(path: str, size: tuple[int, int]) -> Any:
    """Load an image, scale+center-crop it to exactly `size`, return numpy array."""
    import numpy as np
    from PIL import Image

    w, h = size
    img = Image.open(path).convert("RGB")
    scale = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left = (img.width - w) // 2
    top = (img.height - h) // 2
    return np.asarray(img.crop((left, top, left + w, top + h)))


def _image_clip(path: str, seconds: float, size: tuple[int, int]) -> Any:
    """Still image with a slow Ken Burns zoom."""
    from moviepy import CompositeVideoClip, ImageClip

    base = ImageClip(_cover_frame(path, size)).with_duration(seconds)
    zoomed = base.resized(lambda t, d=seconds: 1 + (ZOOM - 1) * t / d)
    return CompositeVideoClip([zoomed.with_position("center")], size=size).with_duration(seconds)


def _video_clip(path: str, seconds: float, size: tuple[int, int]) -> Any:
    """Stock footage: trimmed (or looped) to `seconds`, cover-cropped, muted."""
    from moviepy import VideoFileClip, vfx

    clip = VideoFileClip(path).without_audio()
    if clip.duration < seconds:
        clip = clip.with_effects([vfx.Loop(duration=seconds)])
    else:
        clip = clip.subclipped(0, seconds)
    w, h = size
    scale = max(w / clip.w, h / clip.h)
    clip = clip.resized(scale)
    return clip.cropped(x_center=clip.w / 2, y_center=clip.h / 2, width=w, height=h)


def _render(ws: Workspace, plans: list[dict], settings: Settings) -> None:
    from moviepy import AudioFileClip, concatenate_audioclips, concatenate_videoclips

    size = tuple(settings.video.resolution)
    clips = []
    audio_parts = []
    for plan in plans:
        audio_parts.append(AudioFileClip(str(ws.path / plan["audio"])))
        per_slot = plan["seconds"] / len(plan["slots"])
        for slot in plan["slots"]:
            path = str(ws.path / slot["file"])
            if slot["type"] == "video":
                clips.append(_video_clip(path, per_slot, size))
            else:
                clips.append(_image_clip(path, per_slot, size))

    audio = concatenate_audioclips(audio_parts)
    video = concatenate_videoclips(clips).with_audio(audio).with_duration(audio.duration)
    video.write_videofile(
        str(ws.file(VIDEO_FILE)),
        fps=settings.video.fps,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        logger=None,
    )


class AssemblyStage(Stage):
    name = "assembly"

    def run(self, ws: Workspace, settings: Settings, secrets: Secrets) -> None:
        narration_path = ws.file(NARRATION_FILE)
        visuals_path = ws.file(VISUALS_FILE)
        if not narration_path.exists() or not visuals_path.exists():
            raise StageError("narration.json or visuals.json missing — run earlier stages first")
        narration = json.loads(narration_path.read_text())
        visuals = json.loads(visuals_path.read_text())
        plans = build_timeline(narration, visuals)
        total_slots = sum(len(p["slots"]) for p in plans)
        log.info(
            "rendering %.1f min video: %d units, %d cuts (this takes a while)",
            narration["total_seconds"] / 60, len(plans), total_slots,
        )
        self._render(ws, plans, settings)
        size_mb = ws.file(VIDEO_FILE).stat().st_size / 1_000_000
        log.info("video written: %s (%.0f MB)", VIDEO_FILE, size_mb)

    # separated so tests can patch rendering
    _render = staticmethod(_render)
