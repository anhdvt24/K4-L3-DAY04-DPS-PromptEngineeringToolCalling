"""
app/session.py — In-memory session store + conversation management.

Each session holds:
  - messages: list[dict] of role/content pairs (full history)
  - turns: list of per-turn turn-records (for the eval-like trace)
  - metadata: version, provider, model
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

# Lazy import to avoid circular issues
sys_imported = False


def _ensure_sys():
    global sys_imported
    if not sys_imported:
        import sys as _sys
        _sys_imported = True


class Session:
    """Holds the conversation state for one chat session."""

    def __init__(
        self,
        session_id: str,
        version: str,
        provider: str,
        model: str | None,
        system_prompt: str,
        tools: list[dict[str, Any]],
    ) -> None:
        self.session_id = session_id
        self.version = version
        self.provider = provider
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.turn_index = 0

        # Full conversation messages (system + user/assistant)
        self.messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

        # Per-turn detailed records (eval-style trace)
        self.turns: list[dict[str, Any]] = []

        # History window (last N pairs kept in context)
        self.history_window = 5

    @property
    def turn_count(self) -> int:
        return self.turn_index

    def add_user_message(self, content: str) -> None:
        """Append a user turn and return the new message list."""
        self.turn_index += 1
        self.updated_at = datetime.now(timezone.utc)
        self.messages.append({"role": "user", "content": content})

    def add_turn_record(self, record: dict[str, Any]) -> None:
        self.turns.append(record)
        self.updated_at = datetime.now(timezone.utc)

    def add_assistant_text(self, text: str) -> None:
        """Append assistant text to the last assistant message or create new."""
        self.messages.append({"role": "assistant", "content": text})

    def trim_history(self) -> list[dict[str, str]]:
        """Return messages with only the last N pairs after system prompt."""
        system = self.messages[0:1]  # always keep system
        conversation = self.messages[1:]  # strip system
        # Keep last (history_window * 2) messages
        windowed = conversation[-(self.history_window * 2):]
        return system + windowed

    def last_message_content(self) -> str | None:
        if self.messages and self.messages[-1]["role"] == "user":
            return self.messages[-1]["content"]
        return None

    def to_info(self) -> dict[str, Any]:
        last = None
        for m in reversed(self.messages):
            if m["role"] == "user":
                last = m["content"]
                break
        return {
            "session_id": self.session_id,
            "version": self.version,
            "provider": self.provider,
            "model": self.model,
            "created_at": self.created_at.isoformat(),
            "turn_count": self.turn_index,
            "last_message": last,
        }

    def to_eval_record(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "version": self.version,
            "provider": self.provider,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "tools": self.tools,
            "created_at": self.created_at.isoformat(),
            "turns": self.turns,
        }


class SessionStore:
    """Thread-safe in-memory store for all sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()

    def create(
        self,
        version: str,
        provider: str,
        model: str | None,
        system_prompt: str,
        tools: list[dict[str, Any]],
    ) -> Session:
        session_id = str(uuid.uuid4())[:8]
        with self._lock:
            session = Session(session_id, version, provider, model, system_prompt, tools)
            self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def list_all(self) -> list[Session]:
        with self._lock:
            return list(self._sessions.values())

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)


# Global store — single instance per process
_store: SessionStore | None = None


def get_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore()
    return _store
