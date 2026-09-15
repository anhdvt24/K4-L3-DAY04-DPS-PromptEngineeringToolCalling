"""
run_v2_gemini.py — Helper: Run V2 evaluation with Google Gemini.

V2 hypothesis (vs V1 measured 19/30 = 63.3% case accuracy):

  V1 had two remaining failure clusters (11 cases / 30):
    * 8 wrong_tool cases — Vietnamese `query` passed to English-indexed
      KB/policy tools (T04, T05, T11, T14, T15, T16, T17, M06).
    * 3 wrong_boundary cases — when user wrote "create ticket for [ID]",
      the lookup rule fired first and emitted an extra read tool call
      (T09, T10, T18).

  V2 changes:
    (a) English-Keyword Query Convention in system_prompt_v2.md with a
        canonical English keyword table for each KB category and policy_area.
    (b) Write-Action Priority rule at the top of the tool-selection list so
        "tạo ticket" goes directly to the Confirmation Rule (clarify) without
        pre-emptive lookups.
    (c) tools_v2.yaml reinforces both rules in the relevant tool descriptions
        (search_travel_kb, travel_policy, clarify, check_booking_status,
        lookup_hotel, create_support_ticket).

  Expected: ≥26/30 (≥86.7%) case accuracy; 0 wrong_boundary failures.

Prerequisites (set BEFORE running this script):
    $env:GEMINI_API_KEY = "AIza..."

Usage:
    python scripts/run_v2_gemini.py
    python scripts/run_v2_gemini.py --suite base
    python scripts/run_v2_gemini.py --suite adversarial
    python scripts/run_v2_gemini.py --suite group
    python scripts/run_v2_gemini.py --model gemini-2.5-pro
    python scripts/run_v2_gemini.py --skip-preflight
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2_SYSTEM_PROMPT = ROOT / "artifacts" / "system_prompt_v2.md"
V2_TOOLS = ROOT / "artifacts" / "tools_v2.yaml"


def _has_key() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def _run_preflight(model: str | None) -> bool:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "preflight_provider.py"),
        "--provider", "gemini",
        "--tools", str(V2_TOOLS),
    ]
    if model:
        cmd.extend(["--model", model])
    print("[1/3] Preflight: gọi thử 1 tool call với V2 tools...")
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        return False
    print(proc.stdout.strip())
    return True


def _run_eval(suite: str, model: str | None) -> int:
    suite_to_cases = {
        "base": "data/eval_base_tourism.json",
        "adversarial": "data/eval_adversarial_tourism.json",
        "group": "data/eval_group.json",
    }
    if suite not in suite_to_cases:
        raise SystemExit(f"Unknown suite: {suite}. Use base | adversarial | group.")
    cmd = [
        sys.executable,
        str(ROOT / "run_eval.py"),
        "--provider", "gemini",
        "--version", "v2",
        "--phase", "B",
        "--suite", suite,
        "--system-prompt", str(V2_SYSTEM_PROMPT),
        "--tools", str(V2_TOOLS),
        "--eval-cases", str(ROOT / suite_to_cases[suite]),
    ]
    if model:
        cmd.extend(["--model", model])
    print(f"\n[2/3] Run eval: suite={suite}, prompt={V2_SYSTEM_PROMPT.name}, tools={V2_TOOLS.name}, model={model or 'default'}")
    print(" ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT))
    return proc.returncode


def _print_summary_hint() -> None:
    print("\n[3/3] Sau khi run xong, mở file JSON mới nhất trong runs/ để xem summary.")
    runs_dir = ROOT / "runs"
    if runs_dir.exists():
        files = sorted(runs_dir.glob("v2_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]
        for f in files:
            print(f"  - {f.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run V2 evaluation with Google Gemini.")
    parser.add_argument("--suite", choices=["base", "adversarial", "group"], default="base")
    parser.add_argument("--model", default=None, help="Model override (default: gemini-2.5-flash)")
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()

    if not V2_SYSTEM_PROMPT.exists():
        raise SystemExit(f"V2 system prompt not found: {V2_SYSTEM_PROMPT}")
    if not V2_TOOLS.exists():
        raise SystemExit(f"V2 tools file not found: {V2_TOOLS}")

    if not _has_key():
        raise SystemExit(
            "GEMINI_API_KEY chưa được set. Trước khi chạy, gõ:\n"
            "    $env:GEMINI_API_KEY = \"AIza...\"\n"
            "(Lấy key miễn phí tại https://aistudio.google.com/apikey)"
        )

    if not args.skip_preflight:
        if not _run_preflight(args.model):
            raise SystemExit("Preflight thất bại — kiểm tra key hoặc tên model.")

    rc = _run_eval(args.suite, args.model)
    if rc != 0:
        raise SystemExit(f"Eval exited with code {rc}.")
    _print_summary_hint()


if __name__ == "__main__":
    main()
