"""
Conversation state: message history, context-window trimming, and
persistence of chat sessions to disk as JSON files.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import HISTORY_DIR


def _rough_token_estimate(text: str) -> int:
    """
    Cheap, dependency-free token estimate (~4 chars per token for English).
    Good enough for deciding when to trim; doesn't need to be exact.
    """
    return max(1, len(text) // 4)


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, d: dict) -> Message:
        return cls(role=d["role"], content=d["content"], timestamp=d.get("timestamp", time.time()))


class Conversation:
    def __init__(self, system_prompt: str, context_limit: int, session_id: Optional[str] = None):
        self.system_prompt = system_prompt
        self.context_limit = context_limit
        self.session_id = session_id or time.strftime("%Y%m%d-%H%M%S")
        self.messages: list[Message] = []
        self._trimmed_notice_shown = False

    def add(self, role: str, content: str) -> None:
        self.messages.append(Message(role=role, content=content))

    def to_api_messages(self) -> list[dict]:
        """Build the message list to send to the model, with system prompt + trimming."""
        trimmed = self._trim_if_needed()
        if trimmed and not self._trimmed_notice_shown:
            self._trimmed_notice_shown = True
            # Import here to avoid circular import at module level
            from . import ui
            ui.print_info("[dim](Oldest messages trimmed to stay within context limit.)[/dim]")
        api_messages = [{"role": "system", "content": self.system_prompt}]
        api_messages += [{"role": m.role, "content": m.content} for m in self.messages]
        return api_messages

    def _trim_if_needed(self) -> bool:
        """
        Drop oldest user/assistant turns once the estimated token count
        exceeds the configured context limit.
        """
        total = _rough_token_estimate(self.system_prompt)
        total += sum(_rough_token_estimate(m.content) for m in self.messages)

        trimmed = False
        while total > self.context_limit and len(self.messages) > 2:
            removed = self.messages.pop(0)
            total -= _rough_token_estimate(removed.content)
            trimmed = True
        return trimmed

    def clear(self) -> None:
        self.messages = []

    # --- persistence -----------------------------------------------------

    def save(self) -> Path:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        path = HISTORY_DIR / f"{self.session_id}.json"
        data = {
            "session_id": self.session_id,
            "system_prompt": self.system_prompt,
            "messages": [m.to_dict() for m in self.messages],
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path, context_limit: int) -> "Conversation":
        data = json.loads(path.read_text(encoding="utf-8"))
        convo = cls(
            system_prompt=data.get("system_prompt", ""),
            context_limit=context_limit,
            session_id=data.get("session_id", path.stem),
        )
        convo.messages = []
        for raw_msg in data.get("messages", []):
            try:
                convo.messages.append(Message.from_dict(raw_msg))
            except (KeyError, TypeError):
                # Skip malformed entries rather than crashing the whole load
                continue
        return convo

    @staticmethod
    def list_saved() -> list[Path]:
        if not HISTORY_DIR.exists():
            return []
        return sorted(HISTORY_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
