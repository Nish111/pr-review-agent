"""Run ruff on a PR's head tree and turn warnings on changed lines into Findings."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pr_review.contracts import AgentType, Finding, Severity, Span

# Pre-registered in eval/PREREG_RUNG1.md. Changing this list means writing a new pre-registration.
RULES = ("F", "E9", "B", "S", "DTZ", "BLE", "PERF")
TIMEOUT_SECONDS = 60   # invariant every_outbound_call_is_bounded


def _severity(code: str) -> Severity:
    if code.startswith("S"):
        return Severity.HIGH
    if code.startswith(("B", "DTZ", "BLE")):
        return Severity.MEDIUM
    return Severity.LOW


def ruff_version() -> str:
    out = subprocess.run([sys.executable, "-m", "ruff", "--version"], capture_output=True, text=True,
                         timeout=TIMEOUT_SECONDS)
    return out.stdout.strip()


def run_ruff(tree: Path) -> list[dict]:
    cmd = [sys.executable, "-m", "ruff", "check", "--isolated", "--no-cache", "--output-format=json",
           "--select", ",".join(RULES), "--exit-zero", "."]
    out = subprocess.run(cmd, cwd=tree, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    if out.returncode != 0:
        raise RuntimeError(f"ruff failed ({out.returncode}): {out.stderr.strip()[:300]}")
    return json.loads(out.stdout or "[]")


def review_tree(tree: Path, changed: dict[str, set[int]]) -> list[Finding]:
    """Findings for warnings that sit on lines the PR changed. Sorted, so output order is stable."""
    findings = []
    for w in run_ruff(tree):
        rel = Path(w["filename"]).resolve().relative_to(tree.resolve()).as_posix()
        row = w["location"]["row"]
        end = max(row, w.get("end_location", {}).get("row", row))
        if not any(n in changed.get(rel, set()) for n in range(row, end + 1)):
            continue
        span = Span(rel, row, end)
        findings.append(Finding(
            agent_type=AgentType.STATIC, severity=_severity(w["code"]), category=w["code"],
            summary=w["message"], location=span, confidence=1.0,
            rationale=f"ruff rule {w['code']} ({w.get('url') or 'no url'})", evidence=(span,)))
    return sorted(findings, key=lambda f: (f.location.file_path, f.location.line_start, f.category))
