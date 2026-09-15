"""
app/schemas.py — Pydantic request/response models for the VietTravel Agent API.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────

class ProviderEnum(str, Enum):
    demo = "demo"
    gemini = "gemini"
    openai = "openai"
    openrouter = "openrouter"
    anthropic = "anthropic"


class VersionEnum(str, Enum):
    v0 = "v0"
    v1 = "v1"
    v2 = "v2"
    v3 = "v3"


class AgentStatus(str, Enum):
    waiting_for_user = "waiting_for_user"
    answered = "answered"
    max_tool_rounds = "max_tool_rounds"
    provider_error = "provider_error"


# ── Tool event models ────────────────────────────────────────────────────────

class ToolCallModel(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class ToolResultModel(BaseModel):
    tool: str
    args: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    awaiting_user: bool | None = None
    error: str | None = None


# ── Turn / message models ────────────────────────────────────────────────────

class UserMessage(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1, max_length=4000)
    version: VersionEnum = VersionEnum.v1
    provider: ProviderEnum = ProviderEnum.gemini
    model: str | None = None


class TurnRoundModel(BaseModel):
    round: int
    assistant_text: str | None = None
    tool_calls: list[ToolCallModel] = Field(default_factory=list)
    tool_results: list[ToolResultModel] = Field(default_factory=list)


class TurnResponse(BaseModel):
    session_id: str
    turn_index: int
    status: AgentStatus
    assistant_text: str | None = None
    rounds: list[TurnRoundModel] = Field(default_factory=list)
    tool_events: list[ToolResultModel] = Field(default_factory=list)
    error: str | None = None
    ended_at: datetime


# ── Session models ─────────────────────────────────────────────────────────────

class SessionInfo(BaseModel):
    session_id: str
    version: str
    provider: str
    model: str | None
    created_at: datetime
    turn_count: int
    last_message: str | None = None


class SessionListResponse(BaseModel):
    sessions: list[SessionInfo]
    total: int


# ── Chat message (frontend) ──────────────────────────────────────────────────

class ChatMessage(BaseModel):
    id: str
    role: str  # "user" | "assistant" | "tool-call" | "tool-result"
    content: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: dict[str, Any] | None = None
    status: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Admin / config models ─────────────────────────────────────────────────────

class ConfigResponse(BaseModel):
    available_versions: list[str]
    available_providers: list[str]
    active_version: str
    active_provider: str
    active_model: str | None
    system_prompt_path: str
    tools_path: str
    system_prompt_preview: str = Field(..., max_length=500)


class HealthResponse(BaseModel):
    status: str
    provider_ok: bool
    api_key_present: bool
    gemini_key: bool
    openai_key: bool
    openrouter_key: bool
    anthropic_key: bool
