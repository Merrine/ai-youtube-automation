"""YouTube upload via the Data API v3, OAuth installed-app flow.

First run opens a browser for a one-time authorization; the refresh
token is stored in youtube.token.json (gitignored) and reused forever.
"""

from __future__ import annotations

import logging
from pathlib import Path

from yt_factory.config import Secrets

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = Path("youtube.token.json")
CATEGORY_EDUCATION = "27"


class UploadError(Exception):
    """YouTube upload failed."""


def _fit_tags(tags: list[str], budget: int = 400) -> list[str]:
    """Keep tags within YouTube's ~500-char total limit.

    Multi-word tags count with surrounding quotes plus separators, so stay
    conservative: 400 chars counting each tag as len + 3.
    """
    result: list[str] = []
    used = 0
    for tag in tags:
        tag = tag.strip()[:100]
        cost = len(tag) + 3
        if used + cost > budget:
            break
        result.append(tag)
        used += cost
    return result


class YouTubeUploader:
    def __init__(self, client_secret_file: Path, token_file: Path = TOKEN_FILE) -> None:
        self._client_secret_file = client_secret_file
        self._token_file = token_file

    def _credentials(self):  # noqa: ANN202 — google types are heavy
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        creds = None
        if self._token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self._token_file), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._token_file.write_text(creds.to_json())
        if not creds or not creds.valid:
            if not self._client_secret_file.exists():
                raise UploadError(
                    f"OAuth client secret not found: {self._client_secret_file} — "
                    "download it from Google Cloud Console (APIs & Services > Credentials)"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self._client_secret_file), SCOPES
            )
            creds = flow.run_local_server(port=0)
            self._token_file.write_text(creds.to_json())
            log.info("authorization stored in %s", self._token_file)
        return creds

    def upload(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        privacy: str,
        thumbnail_path: Path | None = None,
    ) -> str:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        youtube = build("youtube", "v3", credentials=self._credentials())
        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:4900],
                "tags": _fit_tags(tags),
                "categoryId": CATEGORY_EDUCATION,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }
        media = MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                log.info("upload progress: %d%%", int(status.progress() * 100))
        video_id = response["id"]
        log.info("uploaded: https://youtu.be/%s (%s)", video_id, privacy)

        if thumbnail_path is not None and thumbnail_path.exists():
            try:
                youtube.thumbnails().set(
                    videoId=video_id, media_body=str(thumbnail_path)
                ).execute()
                log.info("custom thumbnail set")
            except Exception as exc:  # channel not verified for custom thumbnails
                log.warning("thumbnail upload skipped: %s", exc)
        return video_id


def get_uploader(secrets: Secrets) -> YouTubeUploader:
    return YouTubeUploader(secrets.yt_client_secret_file)
