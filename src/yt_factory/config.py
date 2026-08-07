"""Application configuration.

Non-secret settings live in config/settings.yaml.
Secrets (API keys) live in .env / environment variables.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChannelConfig(BaseModel):
    name: str
    lanes: list[str]
    audience: str
    tone: str


class PathsConfig(BaseModel):
    videos_dir: Path
    prompts_dir: Path


class VideoConfig(BaseModel):
    target_minutes: int
    resolution: tuple[int, int]
    fps: int
    max_visual_seconds: float = 6.0


class ProvidersConfig(BaseModel):
    llm: str
    llm_model: str
    tts: str
    tts_voice: str
    images: str


class AutomationConfig(BaseModel):
    gates: list[str]
    upload_visibility: str


class Settings(BaseModel):
    """Validated contents of settings.yaml."""

    channel: ChannelConfig
    paths: PathsConfig
    video: VideoConfig
    providers: ProvidersConfig
    automation: AutomationConfig


class Secrets(BaseSettings):
    """API keys and credentials, loaded from environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    elevenlabs_api_key: str = ""
    openai_api_key: str = ""
    pexels_api_key: str = ""
    yt_client_secret_file: Path = Path("client_secret.json")


@lru_cache
def load_settings(config_file: Path = Path("config/settings.yaml")) -> Settings:
    with config_file.open() as f:
        raw = yaml.safe_load(f)
    return Settings.model_validate(raw)


@lru_cache
def load_secrets() -> Secrets:
    return Secrets()
