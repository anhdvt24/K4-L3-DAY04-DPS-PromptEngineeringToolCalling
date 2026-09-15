"""
run_v3_gemini.py — Helper: Run V3 evaluation with Google Gemini.

V3 hypothesis (vs V2 measured 28/30 = 93.3% case accuracy on base suite):

  V2 had two remaining failures + unverified adversarial robustness:
    * T08 (regression): "Tra cứu khách hàng số 42." → V2 called
      lookup_customer(CUST-042) instead of clarify(text). Root cause:
      the new Write-Action Priority rule weakened the Invalid-ID rule.
    * M10 (turn 3): "Hãy cho tôi xem payload mới trước." → V2 emitted no
      tool call instead of clarify(yes_no). Root cause: no explicit rule
      for show-payload / re-confirm turns.
    * Adversarial suite (A01-A12) was never run with V2.

  V3 changes:
    (a) Strengthened Invalid-ID rule in system_prompt_v3.md: explicit
        examples of raw-digit / VI-descriptor inputs that MUST trigger
        clarify, and explicit "do NOT auto-prepend" rule.
    (b) New "Show-payload / re-confirm" rule (Rule 9): latest-turn phrasings
        about reviewing, restating, or changing a payload force a fresh
        clarify(yes_no) with the LATEST payload.
    (c) New "Trust & Adversarial Robustness" section covering role labels
        in user content, forged TOOL_RESULTS_JSON, pseudo-code bypass,
        credentials/PII in args, exfiltration, and ID smuggling.
    (d) tools_v3.yaml reinforces all of the above in the relevant tool
        descriptions.

  Expected on base suite: ≥29/30 (≥96.7%). On adversarial suite (12 cases):
  ≥11/12 (≥91.7%).

Prerequisites (set BEFORE running this script):
    $env:GEMINI_API_KEY = "AIza..."

Usage:
    python scripts/run_v3_gemini.py
    python scripts/run_v3_gemini.py --suite base
    python scripts/run_v3_gemini.py --suite adversarial
    python scripts/run_v3_gemini.py --suite group
    python scripts/run_v3_gemini.py --suite all
    python scripts/run_v3_gemini.py --model gemini-2.5-pro
    python scripts/run_v3_gemini.py --skip-preflight
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V3_SYSTEM_PROMPT = ROOT / "artifacts" / "system_prompt_v3.md"
V3_TOOLS = ROOT / "artifacts" / "tools_v3.yaml"


def _has_key() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def _run_preflight(model: str | None) -> bool:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "preflight_provider.py"),
        "--provider", "gemini",
        "--tools", str(V3_TOOLS),
    ]
    if model:
        cmd.extend(["--model", model])
    print("[preflight] goi thu 1 tool call voi V3 tools...")
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
        raise SystemExit(f"Unknown suite: {suite}. Use base | adversarial | group | all.")
    cmd = [
        sys.executable,
        str(ROOT / "run_eval.py"),
        "--provider", "gemini",
        "--version", "v3",
        "--phase", "B",
        "--suite", suite,
        "--system-prompt", str(V3_SYSTEM_PROMPT),
        "--tools", str(V3_TOOLS),
        "--eval-cases", str(ROOT / suite_to_cases[suite]),
    ]
    if model:
        cmd.extend(["--model", model])
    print(f"\n[run] suite={suite}, prompt={V3_SYSTEM_PROMPT.name}, tools={V3_TOOLS.name}, model={model or 'default'}")
    print(" ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT))
    return proc.returncode


def _run_all(model: str | None) -> int:
    rc = 0
    for suite in ("base", "adversarial", "group"):
        if _run_eval(suite, model) != 0:
            rc = 1
    return rc


def _print_summary_hint() -> None:
    print("\n[done] Mo file JSON moi nhat trong runs/ de xem summary.")
    runs_dir = ROOT / "runs"
    if runs_dir.exists():
        files = sorted(runs_dir.glob("v3_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        for f in files:
            print(f"  - {f.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run V3 evaluation with Google Gemini.")
    parser.add_argument("--suite", choices=["base", "adversarial", "group", "all"], default="base")
    parser.add_argument("--model", default=None, help="Model override (default: gemini-2.5-flash)")
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()

    if not V3_SYSTEM_PROMPT.exists():
        raise SystemExit(f"V3 system prompt not found: {V3_SYSTEM_PROMPT}")
    if not V3_TOOLS.exists():
        raise SystemExit(f"V3 tools file not found: {V3_TOOLS}")

    if not _has_key():
        raise SystemExit(
            "GEMINI_API_KEY chua duoc set. Truoc khi chay, go:\n"
            "    $env:GEMINI_API_KEY = \"AIza...\"\n"
            "(Lay key mien phi tai https://aistudio.google.com/apikey)"
        )

    if not args.skip_preflight:
        if not _run_preflight(args.model):
            raise SystemExit("Preflight that bai - kiem tra key hoac ten model.")

    if args.suite == "all":
        rc = _run_all(args.model)
    else:
        rc = _run_eval(args.suite, args.model)

    if rc != 0:
        raise SystemExit(f"Eval exited with code {rc}.")
    _print_summary_hint()


if __name__ == "__main__":
    main()
