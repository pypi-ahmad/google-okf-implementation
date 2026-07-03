"""Async Ollama client wrappers for chat and embeddings."""

from typing import Any

import httpx
from loguru import logger

from okfhub.settings import Settings


class OllamaClient:
    """Thin async client for Ollama APIs.

    Example:
        >>> client = OllamaClient(Settings())
        >>> # await client.chat_json(...)
    """

    def __init__(self, settings: Settings):
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._chat_model = settings.ollama_chat_model
        self._embed_model = settings.ollama_embed_model

    async def chat_json(self, prompt: str) -> dict[str, Any]:
        """Call `/api/chat` and parse JSON response body."""

        payload = {
            "model": self._chat_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0},
        }
        url = f"{self._base_url}/api/chat"

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

        message = result.get("message", {})
        content = message.get("content", "{}")
        try:
            return httpx.Response(200, content=content).json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to decode model JSON output: {}", exc)
            return {"raw": content}

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed list of strings using `/api/embed`."""

        if not texts:
            return []

        payload = {"model": self._embed_model, "input": texts}
        url = f"{self._base_url}/api/embed"

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list):
            raise RuntimeError("Unexpected embeddings response from Ollama")
        return embeddings

    async def chat_text(self, prompt: str) -> str:
        """Call `/api/chat` and return plain text output."""

        payload = {
            "model": self._chat_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.1},
        }
        url = f"{self._base_url}/api/chat"

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

        message = result.get("message", {})
        return str(message.get("content", "")).strip()
