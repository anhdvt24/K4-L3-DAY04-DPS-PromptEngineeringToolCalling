"""
app/main.py — FastAPI application for VietTravel Tourism Helpdesk Agent (V1).

Routes:
  GET  /                     — Serve chat UI (HTML)
  GET  /health               — Health check
  GET  /api/config           — Active config info
  GET  /api/sessions         — List all sessions
  GET  /api/sessions/{id}    — Get session detail
  DELETE /api/sessions/{id}  — Delete a session
  POST /api/chat             — Send a message and get agent response
  GET  /api/sessions/{id}/history — Get chat history for a session

Run:
  cd starter_v0
  pip install fastapi uvicorn
  uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

# Import existing project modules (same directory as app/)
import sys as _sys
_ROOT = Path(__file__).resolve().parents[1]
_sys.path.insert(0, str(_ROOT))

from app.schemas import (
    AgentStatus,
    ChatMessage,
    ConfigResponse,
    HealthResponse,
    ProviderEnum,
    SessionInfo,
    SessionListResponse,
    ToolCallModel,
    ToolResultModel,
    TurnResponse,
    TurnRoundModel,
    UserMessage,
    VersionEnum,
)
from app.session import Session, SessionStore, get_store
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools

# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="VietTravel Agent — V1 Chat UI",
    description="FastAPI web interface for the VietTravel Tourism Helpdesk Agent, powered by the V1 system prompt.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ───────────────────────────────────────────────────────────────────

ROOT = _ROOT
ARTIFACTS_DIR = ROOT / "artifacts"

# Version → (system_prompt_path, tools_path)
VERSION_PATHS: dict[str, tuple[Path, Path]] = {
    "v0": (ARTIFACTS_DIR / "system_prompt.md", ARTIFACTS_DIR / "tools.yaml"),
    "v1": (ARTIFACTS_DIR / "system_prompt_v1.md", ARTIFACTS_DIR / "tools_v1.yaml"),
    "v2": (ARTIFACTS_DIR / "system_prompt_v2.md", ARTIFACTS_DIR / "tools_v2.yaml"),
    "v3": (ARTIFACTS_DIR / "system_prompt_v3.md", ARTIFACTS_DIR / "tools_v3.yaml"),
}

DEFAULT_VERSION = "v3"
DEFAULT_PROVIDER = "gemini"


def _load_version_config(version: str) -> tuple[str, list[dict[str, Any]]]:
    """Load system prompt + tool declarations for a version."""
    if version not in VERSION_PATHS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown version {version!r}. Available: {list(VERSION_PATHS)}",
        )
    prompt_path, tools_path = VERSION_PATHS[version]
    if not prompt_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"System prompt not found: {prompt_path}",
        )
    if not tools_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tools file not found: {tools_path}",
        )
    system_prompt = prompt_path.read_text(encoding="utf-8")
    tool_declarations = load_tool_declarations(tools_path)
    return system_prompt, tool_declarations


# ── Tool execution (from chat.py) ─────────────────────────────────────────────

TOOL_FUNCTIONS: dict[str, Any] = {}  # Lazily populated


def _ensure_tool_functions() -> None:
    global TOOL_FUNCTIONS
    if not TOOL_FUNCTIONS:
        # Import here to avoid circular / early dependency issues
        from tools import TOURISM_TOOL_FUNCTIONS
        TOOL_FUNCTIONS = TOURISM_TOOL_FUNCTIONS


def _execute_tool(call: ToolCallModel) -> ToolResultModel:
    _ensure_tool_functions()
    func = TOOL_FUNCTIONS.get(call.name)
    if not func:
        return ToolResultModel(
            tool=call.name,
            args=call.args,
            error=f"unknown_tool: {call.name}",
        )
    try:
        result = func(**call.args)
        awaiting = result.get("awaiting_user") if isinstance(result, dict) else False
        return ToolResultModel(
            tool=call.name,
            args=call.args,
            result=result if isinstance(result, dict) else {"value": result},
            awaiting_user=awaiting,
        )
    except Exception as exc:
        return ToolResultModel(
            tool=call.name,
            args=call.args,
            error=f"{type(exc).__name__}: {exc}",
        )


def _tool_calls_message(calls: list[ToolCallModel], results: list[ToolResultModel]) -> dict[str, str]:
    """Build a user-role message with tool results injected for the next model turn."""
    events = [{"tool": r.tool, "args": r.args or {}, "result": r.result or {}} for r in results]
    content = (
        "TOOL_RESULTS_JSON:\n"
        f"{json.dumps(events, ensure_ascii=False, indent=2)}\n\n"
        "Use these tool results to answer the user's original question. "
        "If the user asked for a support ticket creation and the tool returned needs_confirmation, "
        "explain what will happen and wait. Otherwise answer directly and concisely."
    )
    return {"role": "user", "content": content}


def _assistant_message(text: str | None, calls: list[ToolCallModel]) -> dict[str, str]:
    summary = [{"name": c.name, "args": c.args} for c in calls]
    content = (text or "Tôi đang xử lý yêu cầu của bạn.")
    if summary:
        content += f"\n\nTOOL_CALLS_JSON:\n{json.dumps(summary, ensure_ascii=False, indent=2)}"
    return {"role": "assistant", "content": content}


# ── Agent tool loop (from chat.py, adapted) ───────────────────────────────────

MAX_TOOL_ROUNDS = 4


def _run_agent_loop(
    session: Session,
    user_message: str,
    provider_name: str,
    model: str | None,
) -> TurnResponse:
    _ensure_tool_functions()
    now = datetime.now(timezone.utc)
    turn_index = session.turn_index + 1

    # Add user message to session
    session.add_user_message(user_message)

    # Build working message list (trimmed history)
    working_messages = session.trim_history()

    # Make provider
    try:
        provider = make_provider(provider_name)
    except Exception as exc:
        return TurnResponse(
            session_id=session.session_id,
            turn_index=turn_index,
            status=AgentStatus.provider_error,
            error=f"Provider init failed: {exc}",
            ended_at=datetime.now(timezone.utc),
        )

    tool_declarations = to_openai_tools(session.tools)
    rounds: list[TurnRoundModel] = []
    all_tool_events: list[ToolResultModel] = []
    working_messages = list(working_messages)

    for round_i in range(1, MAX_TOOL_ROUNDS + 1):
        try:
            response = provider.complete(
                working_messages,
                tool_declarations,
                model=model,
                temperature=0.0,
            )
        except Exception as exc:
            return TurnResponse(
                session_id=session.session_id,
                turn_index=turn_index,
                status=AgentStatus.provider_error,
                error=f"Provider call failed: {type(exc).__name__}: {exc}",
                rounds=rounds,
                tool_events=all_tool_events,
                ended_at=datetime.now(timezone.utc),
            )

        tool_calls = [ToolCallModel(name=c.name, args=c.args) for c in response.tool_calls]

        round_record = TurnRoundModel(
            round=round_i,
            assistant_text=response.text,
            tool_calls=tool_calls,
            tool_results=[],
        )
        rounds.append(round_record)

        if not tool_calls:
            # Agent answered without tools
            assistant_text = response.text or ""
            session.add_assistant_text(assistant_text)
            session.add_turn_record({
                "turn_index": turn_index,
                "user": user_message,
                "status": "answered",
                "assistant_text": assistant_text,
                "rounds": [r.model_dump() for r in rounds],
                "tool_events": [e.model_dump() for e in all_tool_events],
                "ended_at": datetime.now(timezone.utc).isoformat(),
            })
            return TurnResponse(
                session_id=session.session_id,
                turn_index=turn_index,
                status=AgentStatus.answered,
                assistant_text=assistant_text,
                rounds=rounds,
                tool_events=all_tool_events,
                ended_at=datetime.now(timezone.utc),
            )

        # Append assistant message with tool calls
        working_messages.append(_assistant_message(response.text, tool_calls))

        # Execute all tool calls
        non_clarification_events: list[ToolResultModel] = []
        for tc in tool_calls:
            result_model = _execute_tool(tc)
            round_record.tool_results.append(result_model)
            all_tool_events.append(result_model)

            result = result_model.result or {}
            if result_model.awaiting_user:
                # Clarification / waiting for user — stop loop
                question = (
                    result.get("question")
                    or tc.args.get("question")
                    or "Xin bổ sung thêm thông tin."
                )
                session.add_turn_record({
                    "turn_index": turn_index,
                    "user": user_message,
                    "status": "waiting_for_user",
                    "assistant_text": question,
                    "rounds": [r.model_dump() for r in rounds],
                    "tool_events": [e.model_dump() for e in all_tool_events],
                    "ended_at": datetime.now(timezone.utc).isoformat(),
                })
                return TurnResponse(
                    session_id=session.session_id,
                    turn_index=turn_index,
                    status=AgentStatus.waiting_for_user,
                    assistant_text=question,
                    rounds=rounds,
                    tool_events=all_tool_events,
                    ended_at=datetime.now(timezone.utc),
                )

            non_clarification_events.append(result_model)

        # Inject tool results and continue loop
        working_messages.append(_tool_calls_message(tool_calls, non_clarification_events))

    # Max rounds reached
    session.add_assistant_text(f"Đã đạt giới hạn {MAX_TOOL_ROUNDS} vòng tool. Vui lòng thử lại hoặc đặt câu hỏi rõ hơn.")
    session.add_turn_record({
        "turn_index": turn_index,
        "user": user_message,
        "status": "max_tool_rounds",
        "assistant_text": f"Stopped after {MAX_TOOL_ROUNDS} tool rounds.",
        "rounds": [r.model_dump() for r in rounds],
        "tool_events": [e.model_dump() for e in all_tool_events],
        "ended_at": datetime.now(timezone.utc).isoformat(),
    })
    return TurnResponse(
        session_id=session.session_id,
        turn_index=turn_index,
        status=AgentStatus.max_tool_rounds,
        assistant_text=f"Đã đạt giới hạn {MAX_TOOL_ROUNDS} vòng tool.",
        rounds=rounds,
        tool_events=all_tool_events,
        ended_at=datetime.now(timezone.utc),
    )


# ── Static files & templates ──────────────────────────────────────────────────

STATIC_DIR = Path(__file__).parent / "static"
TEMPLATE_DIR = Path(__file__).parent / "templates"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Serve the chat UI."""
    html_path = TEMPLATE_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"), status_code=200)
    raise HTTPException(status_code=404, detail="index.html not found")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Check API key presence and overall health."""
    return HealthResponse(
        status="ok",
        provider_ok=True,
        api_key_present=bool(os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")),
        gemini_key=bool(os.getenv("GEMINI_API_KEY")),
        openai_key=bool(os.getenv("OPENAI_API_KEY")),
        openrouter_key=bool(os.getenv("OPENROUTER_API_KEY")),
        anthropic_key=bool(os.getenv("ANTHROPIC_API_KEY")),
    )


# ── Demo mode ────────────────────────────────────────────────────────────────
# Pattern-based mock agent for testing the UI without an API key.
import re as _re

_DEMO_BK = _re.compile(r"\bBK-(\d{3,6})\b", _re.IGNORECASE)
_DEMO_CUST = _re.compile(r"\bCUST-(\d{3,4})\b", _re.IGNORECASE)
_DEMO_HTL = _re.compile(r"\bHTL-([A-Z0-9]{2,4})\b", _re.IGNORECASE)


def _demo_respond(user_text: str) -> dict[str, Any]:
    """Return a simulated turn response based on simple patterns."""
    text = user_text.strip()
    lower = text.lower()
    now = datetime.now(timezone.utc).isoformat()

    # ── Booking pattern ────────────────────────────────────────────────────
    bk = _DEMO_BK.search(text)
    if bk and not _DEMO_HTL.search(text):
        booking_id = f"BK-{bk.group(1)}"
        return {
            "status": "answered",
            "assistant_text": (
                f"[DEMO] Booking {booking_id} đang ở trạng thái 'confirmed'. "
                f"Khách sạn: Vinpearl Resort Nha Trang. Check-in: 2026-10-15. Check-out: 2026-10-18."
            ),
            "rounds": [{
                "round": 1,
                "assistant_text": None,
                "tool_calls": [{"name": "check_booking_status", "args": {"booking_id": booking_id}}],
                "tool_results": [{
                    "tool": "check_booking_status",
                    "args": {"booking_id": booking_id},
                    "result": {"booking_id": booking_id, "status": "confirmed", "hotel": "Vinpearl Resort Nha Trang", "check_in": "2026-10-15"},
                }],
            }],
            "tool_events": [],
            "error": None,
        }

    # ── Hotel pattern ──────────────────────────────────────────────────────
    htl = _DEMO_HTL.search(text)
    if htl:
        hotel_id = f"HTL-{htl.group(1).upper()}"
        return {
            "status": "answered",
            "assistant_text": f"[DEMO] Khách sạn {hotel_id} — Vinpearl Resort, Nha Trang. 4.7★, có hồ bơi, bãi biển riêng.",
            "rounds": [{
                "round": 1,
                "assistant_text": None,
                "tool_calls": [{"name": "lookup_hotel", "args": {"hotel_id": hotel_id}}],
                "tool_results": [{
                    "tool": "lookup_hotel",
                    "args": {"hotel_id": hotel_id},
                    "result": {"hotel_id": hotel_id, "name": "Vinpearl Resort", "city": "Nha Trang", "stars": 4.7},
                }],
            }],
            "tool_events": [],
            "error": None,
        }

    # ── Customer pattern ────────────────────────────────────────────────────
    cust = _DEMO_CUST.search(text)
    if cust:
        customer_id = f"CUST-{cust.group(1)}"
        return {
            "status": "answered",
            "assistant_text": f"[DEMO] Khách hàng {customer_id} — Nguyễn Văn A, hạng Gold, 12 chuyến đã đặt.",
            "rounds": [{
                "round": 1,
                "assistant_text": None,
                "tool_calls": [{"name": "lookup_customer", "args": {"customer_id": customer_id}}],
                "tool_results": [{
                    "tool": "lookup_customer",
                    "args": {"customer_id": customer_id},
                    "result": {"customer_id": customer_id, "name": "Nguyễn Văn A", "tier": "Gold"},
                }],
            }],
            "tool_events": [],
            "error": None,
        }

    # ── Refund / visa / payment keywords → KB ──────────────────────────────
    if any(kw in lower for kw in ["hoàn tiền", "refund", "hủy", "visa", "thanh toán", "payment", "momo", "bảo hiểm", "insurance"]):
        category = "refund" if any(kw in lower for kw in ["hoàn tiền", "refund", "hủy"]) else \
                   "visa" if "visa" in lower else \
                   "payment" if any(kw in lower for kw in ["thanh toán", "payment", "momo"]) else "insurance"
        return {
            "status": "answered",
            "assistant_text": f"[DEMO] Theo chính sách {category} của VietTravel: hoàn 80% nếu hủy trước 7 ngày; visa cần hộ chiếu còn hạn 6 tháng; chấp nhận MoMo/ZaloPay.",
            "rounds": [{
                "round": 1,
                "assistant_text": None,
                "tool_calls": [{"name": "search_travel_kb", "args": {"query": text, "category": category}}],
                "tool_results": [{
                    "tool": "search_travel_kb",
                    "args": {"query": text, "category": category},
                    "result": {"results": [{"title": f"{category.title()} policy", "snippet": "Hoàn 80% nếu hủy trước 7 ngày."}]},
                }],
            }],
            "tool_events": [],
            "error": None,
        }

    # ── Create ticket → always ask clarify (V1 confirmation rule demo) ─────
    if any(kw in lower for kw in ["tạo ticket", "ticket", "lỗi", "sự cố", "phản hồi"]):
        return {
            "status": "waiting_for_user",
            "assistant_text": "Tôi sẽ tạo ticket với thông tin:\n• Summary: " + text[:80] + "\n• Priority: medium\n\nBạn xác nhận tạo ticket này chứ?",
            "rounds": [{
                "round": 1,
                "assistant_text": None,
                "tool_calls": [{"name": "clarify", "args": {"question": text[:80], "response_type": "yes_no"}}],
                "tool_results": [{
                    "tool": "clarify",
                    "args": {"question": text[:80], "response_type": "yes_no"},
                    "result": {"question": text[:80], "response_type": "yes_no", "awaiting_user": True},
                }],
            }],
            "tool_events": [],
            "error": None,
        }

    # ── Meta question → no tool ─────────────────────────────────────────────
    if any(kw in lower for kw in ["bạn là", "giúp được gì", "có thể làm gì"]):
        return {
            "status": "answered",
            "assistant_text": "[DEMO] Tôi là trợ lý AI của VietTravel — hỗ trợ tra cứu booking, khách sạn, khách hàng và chính sách du lịch.",
            "rounds": [{
                "round": 1,
                "assistant_text": "[DEMO] Tôi là trợ lý AI của VietTravel — hỗ trợ tra cứu booking, khách sạn, khách hàng và chính sách du lịch.",
                "tool_calls": [],
                "tool_results": [],
            }],
            "tool_events": [],
            "error": None,
        }

    # ── Fallback ───────────────────────────────────────────────────────────
    return {
        "status": "answered",
        "assistant_text": "[DEMO] Bạn có thể thử: 'Tra cứu BK-1001', 'Thông tin HTL-NT5', 'Visa có cần không?', 'Tạo ticket cho lỗi phòng'.",
        "rounds": [{
            "round": 1,
            "assistant_text": "[DEMO] Bạn có thể thử: 'Tra cứu BK-1001', 'Thông tin HTL-NT5', 'Visa có cần không?', 'Tạo ticket cho lỗi phòng'.",
            "tool_calls": [],
            "tool_results": [],
        }],
        "tool_events": [],
        "error": None,
    }


@app.post("/api/demo/chat")
async def demo_chat(body: UserMessage) -> dict[str, Any]:
    """
    Demo mode — returns mock responses based on simple patterns.
    Useful for testing the UI without an API key.
    """
    store = get_store()
    if body.session_id:
        session = store.get(body.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        system_prompt, tool_declarations = _load_version_config(body.version.value)
        session = store.create(
            version=body.version.value,
            provider="demo",
            model="mock-router",
            system_prompt=system_prompt,
            tools=tool_declarations,
        )

    session.add_user_message(body.message)
    demo = _demo_respond(body.message)

    # Append demo assistant text to session
    if demo.get("assistant_text"):
        session.add_assistant_text(demo["assistant_text"])

    session.add_turn_record({
        "turn_index": session.turn_index,
        "user": body.message,
        "status": demo["status"],
        "assistant_text": demo["assistant_text"],
        "rounds": demo["rounds"],
        "tool_events": demo["tool_events"],
        "ended_at": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "session_id": session.session_id,
        "turn_index": session.turn_index,
        "status": demo["status"],
        "assistant_text": demo["assistant_text"],
        "rounds": demo["rounds"],
        "tool_events": demo["tool_events"],
        "error": demo["error"],
        "ended_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """Return current active configuration."""
    prompt_path = ARTIFACTS_DIR / "system_prompt_v1.md"
    tools_path = ARTIFACTS_DIR / "tools_v1.yaml"
    try:
        prompt_preview = prompt_path.read_text(encoding="utf-8")[:500]
    except Exception:
        prompt_preview = "(not found)"
    return ConfigResponse(
        available_versions=list(VERSION_PATHS.keys()),
        available_providers=["gemini", "openai", "openrouter", "anthropic"],
        active_version=DEFAULT_VERSION,
        active_provider=DEFAULT_PROVIDER,
        active_model=None,
        system_prompt_path=str(prompt_path),
        tools_path=str(tools_path),
        system_prompt_preview=prompt_preview,
    )


@app.get("/api/sessions", response_model=SessionListResponse)
async def list_sessions() -> SessionListResponse:
    """List all active chat sessions."""
    store = get_store()
    sessions = store.list_all()
    infos = [SessionInfo(**s.to_info()) for s in sessions]
    return SessionListResponse(sessions=infos, total=len(infos))


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    """Get a session's messages and turn history."""
    store = get_store()
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {
        "session_id": session.session_id,
        "version": session.version,
        "provider": session.provider,
        "model": session.model,
        "created_at": session.created_at.isoformat(),
        "turn_count": session.turn_count,
        "messages": session.messages,
        "turns": session.turns,
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str) -> dict[str, str]:
    """Delete a session."""
    store = get_store()
    if not store.delete(session_id):
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {"status": "deleted", "session_id": session_id}


@app.get("/api/sessions/{session_id}/history")
async def get_history(session_id: str) -> list[dict[str, Any]]:
    """Get the chat message history for a session."""
    store = get_store()
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session.messages


@app.post("/api/chat", response_model=TurnResponse)
async def chat(body: UserMessage) -> TurnResponse:
    """
    Send a message to the agent and get the response.

    If session_id is provided, continue that conversation.
    Otherwise, create a new session.

    Returns full turn trace including tool calls, results, and status.
    """
    store = get_store()

    if body.session_id:
        session = store.get(body.session_id)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail=f"Session {body.session_id} not found. Start a new session by omitting session_id.",
            )
        # Update version/provider if they changed
        if body.version.value != session.version:
            raise HTTPException(
                status_code=400,
                detail="Cannot change version mid-session. Start a new session.",
            )
    else:
        # Create new session
        system_prompt, tool_declarations = _load_version_config(body.version.value)
        session = store.create(
            version=body.version.value,
            provider=body.provider.value,
            model=body.model,
            system_prompt=system_prompt,
            tools=tool_declarations,
        )

    response = _run_agent_loop(
        session=session,
        user_message=body.message,
        provider_name=body.provider.value,
        model=body.model,
    )
    return response


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup() -> None:
    """Load environment variables on startup."""
    load_lab_env(ROOT)
    print(f"[startup] VietTravel Agent API ready. Default version={DEFAULT_VERSION}")
    print(f"[startup] Artifacts dir: {ARTIFACTS_DIR}")
    print(f"[startup] Available versions: {list(VERSION_PATHS)}")
