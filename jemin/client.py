"""
Unified client interface for AI providers (Ollama, OpenAI, Anthropic).
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generator

import requests

if TYPE_CHECKING:
    import openai as openai_lib
    import anthropic as anthropic_lib


class ClientError(Exception):
    """Raised when an AI provider can't be reached or returns an error."""


# ---------------------------------------------------------------------------
# Known model catalogues — shown even when a provider is offline / no key set
# ---------------------------------------------------------------------------

KNOWN_OLLAMA_MODELS: list[str] = [
    "llama3.2:3b",
    "llama3.2:8b",
    "llama3.1:8b",
    "qwen2.5:3b",
    "qwen2.5:7b",
    "phi3:mini",
    "mistral:7b",
    "gemma2:2b",
    "gemma2:9b",
    "codellama:7b",
    "deepseek-r1:7b",
]

KNOWN_OPENAI_MODELS: list[str] = [
    "gpt-4o",
    "gpt-4o-mini",
    "o1",
    "o1-mini",
    "o3",
    "o3-mini",
    "o4-mini",
]

KNOWN_ANTHROPIC_MODELS: list[str] = [
    "claude-opus-4-5",
    "claude-opus-4-0",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-haiku-20240307",
]


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BaseClient(ABC):
    def __init__(self, model: str, temperature: float = 0.7) -> None:
        self.model = model
        self.temperature = temperature

    @abstractmethod
    def is_alive(self) -> bool:
        """Check whether the provider is reachable and configured."""
        ...

    @abstractmethod
    def list_models(self) -> list[str]:
        """
        Return a list of models for this provider.
        Always returns something — falls back to the known catalogue
        when offline or no API key is set.
        """
        ...

    @abstractmethod
    def chat_stream(
        self, messages: list[dict], model: str | None = None
    ) -> Generator[str, None, None]:
        """
        Stream a chat completion token-by-token (as text chunks).

        messages: list of {"role": "user"|"assistant"|"system", "content": str}
        Yields plain text chunks as they arrive.
        """
        ...


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------

class OllamaClient(BaseClient):
    def __init__(self, host: str, model: str, temperature: float = 0.7) -> None:
        super().__init__(model, temperature)
        self.host = host.rstrip("/")

    def is_alive(self) -> bool:
        """Check whether the local Ollama server is reachable."""
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=3)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def list_models(self) -> list[str]:
        """
        Return pulled local models when Ollama is running,
        or the known catalogue when it is not.
        """
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            r.raise_for_status()
            data = r.json()
            pulled = [m["name"] for m in data.get("models", [])]
            return pulled if pulled else KNOWN_OLLAMA_MODELS
        except requests.RequestException:
            return KNOWN_OLLAMA_MODELS

    def chat_stream(
        self, messages: list[dict], model: str | None = None
    ) -> Generator[str, None, None]:
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": self.temperature},
        }
        try:
            with requests.post(
                f"{self.host}/api/chat", json=payload, stream=True, timeout=120
            ) as resp:
                if resp.status_code == 404:
                    raise ClientError(
                        f"Model '{payload['model']}' not found locally. "
                        f"Pull it first with: ollama pull {payload['model']}"
                    )
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if chunk.get("error"):
                        raise ClientError(chunk["error"])
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if chunk.get("done"):
                        break
        except requests.ConnectionError as exc:
            raise ClientError(
                "Could not connect to Ollama. Is it running? "
                "Start it with: ollama serve"
            ) from exc
        except requests.Timeout as exc:
            raise ClientError("Request to Ollama timed out.") from exc
        except requests.RequestException as exc:
            raise ClientError(f"Ollama request failed: {exc}") from exc


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

class OpenAIClient(BaseClient):
    client: openai_lib.OpenAI | None

    def __init__(self, api_key: str, model: str, temperature: float = 0.7) -> None:
        super().__init__(model, temperature)
        self.api_key = api_key
        if self.api_key:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
        else:
            self.client = None

    def is_alive(self) -> bool:
        return bool(self.api_key)

    def list_models(self) -> list[str]:
        """
        Return live model list when key is set, otherwise the known catalogue.
        Never raises — callers can check is_alive() for key status.
        """
        if not self.api_key or not self.client:
            return KNOWN_OPENAI_MODELS
        try:
            models = self.client.models.list()
            live = sorted(
                m.id for m in models.data
                if any(tag in m.id for tag in ("gpt", "o1", "o3", "o4"))
            )
            return live if live else KNOWN_OPENAI_MODELS
        except Exception:
            return KNOWN_OPENAI_MODELS

    def chat_stream(
        self, messages: list[dict], model: str | None = None
    ) -> Generator[str, None, None]:
        if not self.api_key or not self.client:
            raise ClientError(
                "OpenAI API key is missing. Sign in securely with: /signin openai (or set via: /apikey openai <key>)"
            )
        try:
            stream = self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=self.temperature,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as exc:
            import openai
            if isinstance(exc, openai.AuthenticationError):
                raise ClientError(
                    "Invalid OpenAI API key. Sign in securely with: /signin openai (or set via: /apikey openai <key>)"
                )
            raise ClientError(f"OpenAI request failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

class AnthropicClient(BaseClient):
    client: anthropic_lib.Anthropic | None

    def __init__(self, api_key: str, model: str, temperature: float = 0.7) -> None:
        super().__init__(model, temperature)
        self.api_key = api_key
        if self.api_key:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            self.client = None

    def is_alive(self) -> bool:
        return bool(self.api_key)

    def list_models(self) -> list[str]:
        """Always returns the known Anthropic catalogue."""
        return KNOWN_ANTHROPIC_MODELS

    def chat_stream(
        self, messages: list[dict], model: str | None = None
    ) -> Generator[str, None, None]:
        if not self.api_key or not self.client:
            raise ClientError(
                "Anthropic API key is missing. Sign in securely with: /signin anthropic (or set via: /apikey anthropic <key>)"
            )
        try:
            system_prompt = ""
            anthropic_messages = []
            for m in messages:
                if m["role"] == "system":
                    system_prompt += m["content"] + "\n"
                else:
                    anthropic_messages.append(
                        {"role": m["role"], "content": m["content"]}
                    )

            with self.client.messages.stream(
                model=model or self.model,
                messages=anthropic_messages,
                system=system_prompt.strip(),
                temperature=self.temperature,
                max_tokens=4096,
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as exc:
            import anthropic
            if isinstance(exc, anthropic.AuthenticationError):
                raise ClientError(
                    "Invalid Anthropic API key. Sign in securely with: /signin anthropic (or set via: /apikey anthropic <key>)"
                )
            raise ClientError(f"Anthropic request failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_client(config) -> BaseClient:
    """Return the correct BaseClient subclass for the configured provider."""
    if config.provider == "openai":
        return OpenAIClient(config.openai_api_key, config.model, config.temperature)
    elif config.provider == "anthropic":
        return AnthropicClient(
            config.anthropic_api_key, config.model, config.temperature
        )
    else:
        return OllamaClient(config.host, config.model, config.temperature)


# Backward-compatible alias
ClientFactory = make_client
