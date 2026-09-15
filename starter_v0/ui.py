"""Streamlit chat UI for the Sao Viet Travel assistant.

Shows every tool call with its input, result or error, the artifact version, and
saves the conversation to transcripts/ in the same format as chat.py.

Run from starter_v0:  streamlit run ui.py
"""
from __future__ import annotations

from datetime import datetime
from itertools import zip_longest
from typing import Any

import streamlit as st

from chat import ARTIFACTS_DIR, ROOT, now_iso, run_model_tool_loop, safe_slug, trim_history, write_transcript
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


PROVIDERS = ["gemini", "openrouter", "openai", "anthropic"]


def is_error(result: Any) -> bool:
    return isinstance(result, dict) and "error" in result


def new_session(provider_name: str, version: str, model: str, history_window: int, max_tool_rounds: int) -> None:
    prompt_path = ARTIFACTS_DIR / "system_prompt.md"
    tools_path = ARTIFACTS_DIR / "tools.yaml"
    artifact_version = build_artifact_version(version, prompt_path, tools_path)
    provider = make_provider(provider_name)
    transcript_id = "_".join([safe_slug(version), safe_slug(provider_name), "ui", datetime.now().strftime("%Y%m%dT%H%M%S%f")])
    st.session_state.update(
        provider=provider,
        system_prompt=prompt_path.read_text(encoding="utf-8"),
        tools=to_openai_tools(load_tool_declarations(tools_path)),
        model=model or None,
        history=[],
        transcript_path=ROOT / "transcripts" / f"{transcript_id}.transcript.json",
        transcript={
            "transcript_id": transcript_id,
            **artifact_version_dict(artifact_version),
            "provider": provider_name,
            "model": model or getattr(provider, "default_model", None),
            "interface": "streamlit_ui",
            "system_prompt": str(prompt_path),
            "tools": str(tools_path),
            "history_window": history_window,
            "max_tool_rounds": max_tool_rounds,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "turns": [],
        },
    )


def render_turn(turn: dict[str, Any]) -> None:
    with st.chat_message("user"):
        st.markdown(turn["user"])
    with st.chat_message("assistant"):
        if turn["status"] == "provider_error":
            st.error(f"Provider error: {turn['error']}")
            return
        st.markdown(turn.get("assistant_text") or "_(no text)_")
        for round_record in turn.get("rounds", []):
            for call, event in zip_longest(round_record["tool_calls"], round_record["tool_results"]):
                if call is None:
                    continue
                result = (event or {}).get("result")
                failed = is_error(result)
                status = "ERROR" if failed else ("NOT RUN" if event is None else "OK")
                with st.expander(f"[{status}] round {round_record['round']} · tool `{call['name']}`", expanded=failed):
                    st.caption("Input (args sent by the model)")
                    st.json(call["args"])
                    if event is None:
                        st.warning("Not executed: the agent paused earlier in this round to wait for the user.")
                    elif failed:
                        st.error(f"Tool error: {result.get('error')} — {result.get('message', '')}")
                        st.json(result)
                    else:
                        st.caption("Result")
                        st.json(result)
        st.caption(f"turn {turn['turn_index']} · status: {turn['status']}")


st.set_page_config(page_title="Sao Viet Travel Assistant", layout="wide")

with st.sidebar:
    st.header("Session")
    provider_name = st.selectbox("Provider", PROVIDERS)
    version = st.text_input("Artifact version label", value="v3")
    model = st.text_input("Model override (optional)", value="")
    history_window = int(st.number_input("History window (turn pairs)", min_value=0, max_value=20, value=5))
    max_tool_rounds = int(st.number_input("Max tool rounds", min_value=1, max_value=8, value=4))
    if st.button("Start new session", type="primary") or "transcript" not in st.session_state:
        new_session(provider_name, version, model, history_window, max_tool_rounds)
    transcript = st.session_state.transcript
    st.markdown("**artifact_version**")
    st.code(transcript["artifact_version"], language=None)
    st.markdown(f"provider: `{transcript['provider']}`  \nmodel: `{transcript['model']}`")
    st.markdown(f"transcript: `{st.session_state.transcript_path.relative_to(ROOT).as_posix()}`")
    st.caption("Settings apply after pressing Start new session.")

st.title("Sao Viet Travel Assistant")
st.caption("Fictional tour operator with mock data. Every tool call, its input and its result or error is shown under the reply.")

for past_turn in st.session_state.transcript["turns"]:
    render_turn(past_turn)

if user_text := st.chat_input("Hỏi về tour, chuyến bay, cẩm nang, chính sách hoặc đặt tour..."):
    transcript = st.session_state.transcript
    messages = [
        {"role": "system", "content": st.session_state.system_prompt},
        *trim_history(st.session_state.history, transcript["history_window"]),
        {"role": "user", "content": user_text},
    ]
    turn: dict[str, Any] = {
        "turn_index": len(transcript["turns"]) + 1,
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }
    with st.spinner("Agent is working..."):
        try:
            turn.update(run_model_tool_loop(
                provider=st.session_state.provider,
                messages=messages,
                tools=st.session_state.tools,
                model=st.session_state.model,
                max_tool_rounds=transcript["max_tool_rounds"],
            ))
            st.session_state.history += [
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": turn["assistant_text"]},
            ]
        except Exception as exc:
            turn.update(status="provider_error", error=f"{type(exc).__name__}: {exc}")
    turn["ended_at"] = now_iso()
    transcript["turns"].append(turn)
    write_transcript(st.session_state.transcript_path, transcript)
    st.rerun()
