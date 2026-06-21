"""
Unified client interface for AI providers (Ollama, OpenAI, Anthropic).
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Generator, Optional

import requests


class ClientError(Exception):
    """Raised when an AI provider can't be reached or returns an error."""


class BaseClient(ABC):
    def __init__(self, model: str, temperature: float = 0.7):
        self.model = model
        self.temperature = temperature

    @abstractmethod
    def is_alive(self) -> bool:
        """Check whether the provider is reachable and configured."""
        pass

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return a list of available models for this provider."""
        pass

    @abstractmethod
    def chat_stream(
        self, messages: list[dict], model: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Stream a chat completion token-by-token (as text chunks).

        messages: list of {"role": "user"|"assistant"|"system", "content": str}
        Yields plain text chunks as they arrive.
        """
        pass


class OllamaClient(BaseClient):
    def __init__(self, host: str, model: str, temperature: float = 0.7):
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
        """Return the names of models already pulled locally."""
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            r.raise_for_status()
            data = r.json()
            return [m["name"] for m in data.get("models", [])]
        except requests.ConnectionError as exc:
            raise ClientError(
                "Could not connect to Ollama. Is it running? Start it with: ollama serve"
            ) from exc
        except requests.RequestException as exc:
            raise ClientError(f"Could not list local models: {exc}") from exc

    def chat_stream(
        self, messages: list[dict], model: Optional[str] = None
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


class OpenAIClient(BaseClient):
    def __init__(self, api_key: str, model: str, temperature: float = 0.7):
        super().__init__(model, temperature)
        self.api_key = api_key
        if self.api_key:
            import openai
            self.client = openai.Client(api_key=api_key)
        else:
            self.client = None

    def is_alive(self) -> bool:
        return bool(self.api_key)

    def list_models(self) -> list[str]:
        if not self.api_key or not self.client:
            raise ClientError("OpenAI API key is missing. Set it with: /apikey openai <key>")
        try:
            models = self.client.models.list()
            return sorted([m.id for m in models.data if "gpt" in m.id or "o1" in m.id])
        except Exception as exc:
            raise ClientError(f"OpenAI error: {exc}") from exc

    def chat_stream(
        self, messages: list[dict], model: Optional[str] = None
    ) -> Generator[str, None, None]:
        if not self.api_key or not self.client:
            raise ClientError("OpenAI API key is missing. Set it with: /apikey openai <key>")
        try:
            import openai
            stream = self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=self.temperature,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except openai.AuthenticationError:
            raise ClientError("Invalid OpenAI API key. Set it with: /apikey openai <key>")
        except Exception as exc:
            raise ClientError(f"OpenAI request failed: {exc}") from exc


class AnthropicClient(BaseClient):
    def __init__(self, api_key: str, model: str, temperature: float = 0.7):
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
        if not self.api_key:
            raise ClientError("Anthropic API key is missing. Set it with: /apikey anthropic <key>")
        return [
            "claude-3-5-sonnet-20240620",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]

    def chat_stream(
        self, messages: list[dict], model: Optional[str] = None
    ) -> Generator[str, None, None]:
        if not self.api_key or not self.client:
            raise ClientError("Anthropic API key is missing. Set it with: /apikey anthropic <key>")
        try:
            import anthropic

            system_prompt = ""
            anthropic_messages = []
            for m in messages:
                if m["role"] == "system":
                    system_prompt += m["content"] + "\n"
                else:
                    anthropic_messages.append({"role": m["role"], "content": m["content"]})

            with self.client.messages.stream(
                model=model or self.model,
                messages=anthropic_messages,
                system=system_prompt.strip(),
                temperature=self.temperature,
                max_tokens=4096,
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except anthropic.AuthenticationError:
            raise ClientError("Invalid Anthropic API key. Set it with: /apikey anthropic <key>")
        except Exception as exc:
            raise ClientError(f"Anthropic request failed: {exc}") from exc


def ClientFactory(config) -> BaseClient:
    if config.provider == "openai":
        return OpenAIClient(config.openai_api_key, config.model, config.temperature)
    elif config.provider == "anthropic":
        return AnthropicClient(config.anthropic_api_key, config.model, config.temperature)
    else:
        return OllamaClient(config.host, config.model, config.temperature)
