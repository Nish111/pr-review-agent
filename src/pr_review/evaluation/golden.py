"""Load and check the golden PR set.

The check is deliberately strict and deterministic: if it passes, every label points at a real file and
line in the PR's head version, and at a line the PR actually changed. A label on an untouched line would
reward a reviewer for commenting on code outside the PR.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from pr_review.contracts import ContractError, Span

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def changed_lines(diff_text: str) -> dict[str, set[int]]:
    """Head-side line numbers added or modified by a unified diff, per file."""
    out: dict[str, set[int]] = {}
    path, line = None, 0
    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            target = raw[4:].strip()
            path = None if target == "/dev/null" else target.removeprefix("b/")
            if path:
                out.setdefault(path, set())
        elif raw.startswith("@@"):
            m = _HUNK.match(raw)
            line = int(m.group(1)) if m else 0
        elif path is None or raw.startswith("--- "):
            continue
        elif raw.startswith("+"):
            out[path].add(line)
            line += 1
        elif raw.startswith("-"):
            continue
        else:
            line += 1
    return out


@dataclass(frozen=True)
class CheckResult:
    total: int
    planted: int      # PRs with at least one known problem
    clean: int
    real: int
    known_problems: int   # distinct problems (a real problem may span several label ranges)
    problems: tuple[str, ...]   # what is wrong with the label file itself

    @property
    def ok(self) -> bool:
        return not self.problems


def check(labels_path: Path, repo_root: Path) -> CheckResult:
    data = json.loads(labels_path.read_text(encoding="utf-8"))
    problems: list[str] = []
    prs = data.get("prs", [])
    seen: set[str] = set()
    for pr in prs:
        pid = pr.get("id", "?")
        if pid in seen:
            problems.append(f"{pid}: duplicate id")
        seen.add(pid)
        diff_path = repo_root / pr.get("diff", "")
        if not diff_path.is_file():
            problems.append(f"{pid}: diff file missing ({pr.get('diff')})")
            continue
        changed = changed_lines(diff_path.read_text(encoding="utf-8"))
        if pr.get("clean") != (not pr.get("expected")):
            problems.append(f"{pid}: 'clean' flag disagrees with its labels")
        for i, e in enumerate(pr.get("expected", [])):
            try:
                span = Span(e["file_path"], e["line_start"], e["line_end"])
            except (KeyError, ContractError) as err:
                problems.append(f"{pid} label {i}: invalid ({err})")
                continue
            touched = changed.get(span.file_path, set())
            if not any(n in touched for n in range(span.line_start, span.line_end + 1)):
                problems.append(f"{pid} label {i}: {span.file_path}:{span.line_start}-{span.line_end} "
                                f"is not on a line the PR changed")
    planted = sum(1 for p in prs if p.get("expected"))
    known = sum(len({e.get("problem", f"{p.get('id')}/{i}") for i, e in enumerate(p.get("expected", []))})
                for p in prs)
    return CheckResult(total=len(prs), planted=planted, clean=len(prs) - planted,
                       real=sum(1 for p in prs if p.get("source") == "real"), known_problems=known,
                       problems=tuple(problems))
