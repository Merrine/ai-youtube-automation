"""Stock image provider abstraction."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

import requests

from yt_factory.config import Secrets, Settings

log = logging.getLogger(__name__)


class ImageError(Exception):
    """Image search or download failed."""


class MediaProvider(Protocol):
    def fetch_image(
        self, query: str, out_file: Path, exclude: set[str] | None = None
    ) -> dict | None:
        """Save the best matching photo not in `exclude` to `out_file`.

        Returns attribution ({media_id, url, photographer}) or None.
        """
        ...

    def fetch_video(
        self, query: str, out_file: Path, exclude: set[str] | None = None
    ) -> dict | None:
        """Save the best matching video clip not in `exclude` to `out_file`.

        Returns attribution ({media_id, url, photographer}) or None.
        """
        ...


class PexelsProvider:
    """Pexels photo + video search. Free API, license-safe for YouTube."""

    PHOTO_URL = "https://api.pexels.com/v1/search"
    VIDEO_URL = "https://api.pexels.com/videos/search"
    MIN_CLIP_SECONDS = 4
    TARGET_HEIGHT = 1080

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ImageError("PEXELS_API_KEY is empty — add it to .env")
        self._headers = {"Authorization": api_key}

    def fetch_image(
        self, query: str, out_file: Path, exclude: set[str] | None = None
    ) -> dict | None:
        response = requests.get(
            self.PHOTO_URL,
            headers=self._headers,
            params={"query": query, "per_page": 5, "orientation": "landscape", "size": "large"},
            timeout=30,
        )
        response.raise_for_status()
        exclude = exclude or set()
        photos = [
            p for p in response.json().get("photos", []) if f"photo:{p['id']}" not in exclude
        ]
        if not photos:
            log.warning("no unused Pexels photo for query '%s'", query)
            return None
        photo = photos[0]
        image_url = photo["src"].get("large2x") or photo["src"]["large"]
        self._download(image_url, out_file)
        return {
            "media_id": f"photo:{photo['id']}",
            "url": photo["url"],
            "photographer": photo["photographer"],
        }

    def fetch_video(
        self, query: str, out_file: Path, exclude: set[str] | None = None
    ) -> dict | None:
        response = requests.get(
            self.VIDEO_URL,
            headers=self._headers,
            params={"query": query, "per_page": 5, "orientation": "landscape"},
            timeout=30,
        )
        response.raise_for_status()
        exclude = exclude or set()
        videos = [
            v for v in response.json().get("videos", [])
            if v.get("duration", 0) >= self.MIN_CLIP_SECONDS
            and f"video:{v['id']}" not in exclude
        ]
        if not videos:
            log.info("no unused Pexels video for query '%s'", query)
            return None
        video = videos[0]
        file = self._pick_video_file(video.get("video_files", []))
        if file is None:
            return None
        self._download(file["link"], out_file)
        return {
            "media_id": f"video:{video['id']}",
            "url": video["url"],
            "photographer": video["user"]["name"],
        }

    def _pick_video_file(self, files: list[dict]) -> dict | None:
        """Smallest file that still looks sharp: prefer 720-1080p, mp4."""
        candidates = [
            f for f in files
            if f.get("file_type") == "video/mp4" and 720 <= (f.get("height") or 0) <= 1080
        ]
        if not candidates:
            candidates = [f for f in files if f.get("file_type") == "video/mp4"]
        if not candidates:
            return None
        return min(candidates, key=lambda f: abs((f.get("height") or 0) - 1080))

    def _download(self, url: str, out_file: Path) -> None:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        out_file.write_bytes(response.content)


def get_images(settings: Settings, secrets: Secrets) -> MediaProvider:
    name = settings.providers.images
    if name == "pexels":
        return PexelsProvider(secrets.pexels_api_key)
    raise ImageError(f"Unknown image provider '{name}' (supported: pexels)")
