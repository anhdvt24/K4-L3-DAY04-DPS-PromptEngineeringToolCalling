"""Local sensitive-input boundary, shared by eval, CLI and UI.

This is a deterministic guard, not evidence of model refusal quality.
It detects common secret formats, not every possible personal-data encoding.
"""
from __future__ import annotations

import re
from typing import Any

from tools._shared import fold_text
from tools._travel import contains_sensitive_data


SECRET_ASSIGNMENT = re.compile(
    r"\b(?:password|mat khau|api[_ -]?key|access[_ -]?token|recovery[_ -]?code)"
    r"\s*[:=]\s*\S+", re.IGNORECASE,
)
REDACTED = "[REDACTED: sensitive data]"
REFUSAL = (
    "Mình không tiếp nhận hoặc lưu số thẻ, CVV, OTP, mật khẩu hay số giấy tờ "
    "qua chat. Bạn hãy dùng kênh thanh toán/hỗ trợ chính thức và gửi lại "
    "yêu cầu không chứa các giá trị này."
)


def is_sensitive(text: str) -> bool:
    return contains_sensitive_data(text) or bool(SECRET_ASSIGNMENT.search(fold_text(text)))


def redact(value: Any) -> Any:
    """Redact whole strings; never persist or echo a partially exposed secret."""
    if isinstance(value, str):
        return REDACTED if is_sensitive(value) else value
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        return {redact(key): redact(item) for key, item in value.items()}
    return value


def sensitive_user_input(messages: list[dict[str, str]]) -> bool:
    latest = next((m for m in reversed(messages) if m.get("role") == "user"), {})
    return is_sensitive(latest.get("content", ""))


def safe_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    return [dict(m, content=redact(m.get("content", ""))) if m.get("role") != "system" else m.copy()
            for m in messages]
