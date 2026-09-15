"""
run_v1_gemini.py — Helper: Run V1 evaluation with Google Gemini.

V1 hypothesis: Adding the Confirmation Rule (mandatory `clarify` before
`create_support_ticket`) plus the Invalid-ID → clarify rule will raise the
boundary accuracy from 0% (V0) to ≥80%, while preserving routing gains.

Prerequisites (set BEFORE running this script):
    $env:GEMINI_API_KEY = "AIza..."

Usage:
    python scripts/run_v1_gemini.py
    python scripts/run_v1_gemini.py --suite base
    python scripts/run_v1_gemini.py --suite adversarial
    python scripts/run_v1_gemini.py --suite group
    python scripts/run_v1_gemini.py --model gemini-2.5-pro
    python scripts/run_v1_gemini.py --skip-preflight
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1_SYSTEM_PROMPT = ROOT / "artifacts" / "system_prompt_v1.md"
V1_TOOLS = ROOT / "artifacts" / "tools_v1.yaml"


def _has_key() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def _run_preflight(model: str | None) -> bool:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "preflight_provider.py"),
        "--provider", "gemini",
        "--tools", str(V1_TOOLS),
    ]
    if model:
        cmd.extend(["--model", model])
    print("[1/3] Preflight: gọi thử 1 tool call với V1 tools...")
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
        "--version", "v1",
        "--phase", "B",
        "--suite", suite,
        "--system-prompt", str(V1_SYSTEM_PROMPT),
        "--tools", str(V1_TOOLS),
        "--eval-cases", str(ROOT / suite_to_cases[suite]),
    ]
    if model:
        cmd.extend(["--model", model])
    print(f"\n[2/3] Run eval: suite={suite}, prompt={V1_SYSTEM_PROMPT.name}, tools={V1_TOOLS.name}, model={model or 'default'}")
    print(" ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT))
    return proc.returncode


def _print_summary_hint() -> None:
    print("\n[3/3] Sau khi run xong, mở file JSON mới nhất trong runs/ để xem summary.")
    runs_dir = ROOT / "runs"
    if runs_dir.exists():
        files = sorted(runs_dir.glob("v1_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]
        for f in files:
            print(f"  - {f.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run V1 evaluation with Google Gemini.")
    parser.add_argument("--suite", choices=["base", "adversarial", "group"], default="base")
    parser.add_argument("--model", default=None, help="Model override (default: gemini-2.5-flash)")
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()

    if not V1_SYSTEM_PROMPT.exists():
        raise SystemExit(f"V1 system prompt not found: {V1_SYSTEM_PROMPT}")
    if not V1_TOOLS.exists():
        raise SystemExit(f"V1 tools file not found: {V1_TOOLS}")

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
