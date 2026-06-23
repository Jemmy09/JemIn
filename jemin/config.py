"""
Configuration management for Jem In.

Settings are stored in a JSON file under the user's home directory so they
persist across sessions: ~/.jemin/config.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

APP_DIR = Path.home() / ".jemin"
CONFIG_PATH = APP_DIR / "config.json"
HISTORY_DIR = APP_DIR / "conversations"

DEFAULT_SYSTEM_PROMPT = (
    "You are Jem In, a helpful, precise, and honest AI assistant. "
    "Keep answers clear and to the point. "
    "If you are unsure about something, say so plainly instead of guessing."
)

DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_HOST = "http://localhost:11434"
DEFAULT_CONTEXT_LIMIT = 8000  # approx tokens kept before auto-trimming history
DEFAULT_TEMPERATURE = 0.7


@dataclass
class Config:
    model: str = DEFAULT_MODEL
    host: str = DEFAULT_HOST
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    context_limit: int = DEFAULT_CONTEXT_LIMIT
    temperature: float = DEFAULT_TEMPERATURE
    provider: str = "ollama"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    theme: str = "default"  # reserved for future color theme switching

    @classmethod
    def load(cls) -> "Config":
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
                return cls(**known)
            except (json.JSONDecodeError, OSError, TypeError):
                return cls()
        return cls()

    def save(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def ensure_dirs() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
