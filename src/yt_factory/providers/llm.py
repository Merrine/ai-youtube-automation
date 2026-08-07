"""LLM provider abstraction. Swap providers via settings.yaml, not code."""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from yt_factory.config import Secrets, Settings

log = logging.getLogger(__name__)


class LLMError(Exception):
    """LLM call failed or returned unusable output."""


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str: ...

    def generate_json(self, prompt: str) -> Any: ...


class GeminiProvider:
    """Google Gemini via the google-genai SDK. Free tier friendly."""

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise LLMError("GEMINI_API_KEY is empty — add it to .env")
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(self, prompt: str) -> str:
        response = self._client.models.generate_content(model=self._model, contents=prompt)
        if not response.text:
            raise LLMError("Gemini returned empty response")
        return response.text

    def generate_json(self, prompt: str) -> Any:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        if not response.text:
            raise LLMError("Gemini returned empty response")
        try:
            return json.loads(response.text)
        except json.JSONDecodeError as exc:
            log.warning("Gemini returned invalid JSON, retrying once: %s", exc)
            retry = self._client.models.generate_content(
                model=self._model,
                contents=prompt + "\n\nReturn ONLY valid JSON.",
                config={"response_mime_type": "application/json"},
            )
            try:
                return json.loads(retry.text or "")
            except json.JSONDecodeError as exc2:
                raise LLMError(f"Gemini returned invalid JSON twice: {exc2}") from exc2


def get_llm(settings: Settings, secrets: Secrets) -> LLMProvider:
    name = settings.providers.llm
    if name == "gemini":
        return GeminiProvider(secrets.gemini_api_key, settings.providers.llm_model)
    raise LLMError(f"Unknown LLM provider '{name}' (supported: gemini)")
