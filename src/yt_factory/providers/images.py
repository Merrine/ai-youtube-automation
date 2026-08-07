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


class ImageProvider(Protocol):
    def fetch(self, query: str, out_file: Path) -> dict | None:
        """Find the best image for `query`, save it to `out_file`.

        Returns attribution info ({url, photographer}) or None if no result.
        """
        ...


class PexelsProvider:
    """Pexels photo search. Free API, license-safe for YouTube."""

    SEARCH_URL = "https://api.pexels.com/v1/search"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ImageError("PEXELS_API_KEY is empty — add it to .env")
        self._headers = {"Authorization": api_key}

    def fetch(self, query: str, out_file: Path) -> dict | None:
        response = requests.get(
            self.SEARCH_URL,
            headers=self._headers,
            params={"query": query, "per_page": 1, "orientation": "landscape", "size": "large"},
            timeout=30,
        )
        response.raise_for_status()
        photos = response.json().get("photos", [])
        if not photos:
            log.warning("no Pexels result for query '%s'", query)
            return None
        photo = photos[0]
        image_url = photo["src"].get("large2x") or photo["src"]["large"]
        image = requests.get(image_url, timeout=60)
        image.raise_for_status()
        out_file.write_bytes(image.content)
        return {"url": photo["url"], "photographer": photo["photographer"]}


def get_images(settings: Settings, secrets: Secrets) -> ImageProvider:
    name = settings.providers.images
    if name == "pexels":
        return PexelsProvider(secrets.pexels_api_key)
    raise ImageError(f"Unknown image provider '{name}' (supported: pexels)")
