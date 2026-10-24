"""Derive labels for the real pallets/click PRs from click's own history (deterministic, SZZ-style).

Run (needs a local clone of click; the path is yours to choose, outside this repo):
    git clone https://github.com/pallets/click.git ../click
    python golden/real/build_real.py ../click golden

Only (introducing PR, fixing PR) pairs that click itself names are used: in CHANGES.md ("regression
introduced in 8.4.0 by #1572") or in the fixing commit's title ("...introduced in 262bdf0"). For each fix:
  1. lines the fix deleted/modified under src/ (for a pure insertion: the line before and after it)
     are blamed in the fix's parent;
  2. a blamed line counts if its commit belongs to the introducing PR (intro^1..intro);
  3. its text is located in the introducing PR's head version, restricted to lines that PR changed
     (a text match alone would hit unrelated duplicate lines such as a lone ")");
  4. consecutive lines become one label range. All ranges from one fix share a `problem` id, so a
     reviewer finding any of them counts as finding that problem once.
"""

from __future__ import annotations

import collections
import json
import re
import subprocess
import sys
from pathlib import Path

# id, introducing commit (PR head), introducing PR, [(fix commit, fix PR)], issues, what click says
PAIRS = [
    ("R1", "2468b70", "2969", [("fe3ad76", "3653")], ["3572"],
     "CHANGES.md 8.5.0: confirm()/prompt() ANSI stripping 'was lost in 8.4.0 when #2969 began writing the "
     "prompt with input() directly'"),
    ("R2", "c69643b", "1572", [("8b44edf", "3739"), ("fc5c7f4", "3764")], ["3731", "3732", "3740"],
     "CHANGES.md 8.5.0: get_pager_file temp-file backend opened its file in binary mode, 'Regression introduced "
     "in 8.4.0 by #1572'; and it unlinked the file without closing it, masking the real error on Windows"),
    ("R3", "19fd4d6", "3126", [("b7e5fd4", "3504")], ["3502", "3043"],
     "CHANGES.md 8.4.2: 'Fix Fish shell completion broken in 8.4.0 by #3126'"),
    ("R4", "262bdf0", "2934", [("2a0e3ba", "2940")], ["2939"],
     "Fix commit title: 'testing/CliRunner: Fix regression related to EOF introduced in 262bdf0 (#2940)'"),
    ("R5", "8762c77", "(commit 'Expose original file descriptor in CliRunner', fixes issue 2865)",
     [("d959898", "3391")], ["3384"],
     "CHANGES.md 8.4.0: reverts the 8.3.3 change exposing the original fd via fileno() on CliRunner streams, "
     "which 'broke Pytest's fd-level capture teardown'"),
]


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def changed_head_lines(diff: str) -> dict[str, set[int]]:
    out: dict[str, set[int]] = collections.defaultdict(set)
    path, ln = None, 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            t = raw[4:]
            path = None if t == "/dev/null" else t[2:]
        elif raw.startswith("@@"):
            ln = int(re.match(r"@@ -\S+ \+(\d+)", raw).group(1))
        elif path is None or raw.startswith("--- "):
            continue
        elif raw.startswith("+"):
            out[path].add(ln)
            ln += 1
        elif not raw.startswith("-"):
            ln += 1
    return out


def traced_texts(repo: Path, fix: str, pr_commits: set[str]) -> dict[str, set[str]]:
    texts: dict[str, set[str]] = collections.defaultdict(set)
    d = git(repo, "diff", "-U0", "--no-renames", f"{fix}^1", fix, "--", "src")
    path = None
    for line in d.splitlines():
        if line.startswith("--- a/"):
            path = line[6:]
        elif line.startswith("--- /dev/null"):
            path = None
        elif line.startswith("@@") and path:
            m = re.match(r"@@ -(\d+)(?:,(\d+))?", line)
            s, n = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
            lo, hi = (s, s + n - 1) if n > 0 else (max(1, s), s + 1)
            cur = None
            for bl in git(repo, "blame", "--porcelain", "-L", f"{lo},{hi}", f"{fix}^1", "--", path).splitlines():
                mm = re.match(r"^([0-9a-f]{40}) \d+ \d+", bl)
                if mm:
                    cur = mm.group(1)
                elif bl.startswith("\t") and cur in pr_commits and bl[1:].strip():
                    texts[path].add(bl[1:])
    return texts


def build(repo: Path, prs_dir: Path) -> list[dict]:
    prs_dir.mkdir(parents=True, exist_ok=True)
    prs = []
    for pid, intro, ipr, fixes, issues, quote in PAIRS:
        base = git(repo, "log", "-1", "--format=%P", intro).split()[0]
        pr_commits = set(git(repo, "rev-list", f"{base}..{intro}").split())
        diff = git(repo, "diff", "--no-renames", base, intro, "--", "src")
        (prs_dir / f"{pid}.diff").write_text(diff, encoding="utf-8", newline="\n")
        added = changed_head_lines(diff)
        expected = []
        for fix, fpr in fixes:
            for path, texts in sorted(traced_texts(repo, fix, pr_commits).items()):
                head = git(repo, "show", f"{intro}:{path}").splitlines()
                lines = sorted(i for i, h in enumerate(head, 1) if h in texts and i in added.get(path, set()))
                ranges: list[list[int]] = []
                for n in lines:
                    if ranges and n == ranges[-1][1] + 1:
                        ranges[-1][1] = n
                    else:
                        ranges.append([n, n])
                for a, b in ranges:
                    expected.append({"file_path": path, "line_start": a, "line_end": b, "severity": "high",
                                     "specialist": "any", "category": "regression",
                                     "problem": f"{pid}/fix#{fpr}", "description": quote})
        prs.append({"id": pid, "source": "real", "repo": "pallets/click", "intro_commit": intro,
                    "intro_pr": ipr, "fix": [{"commit": c, "pr": p} for c, p in fixes], "issues": issues,
                    "title": git(repo, "log", "-1", "--format=%s", intro).strip(),
                    "changed_lines": sum(1 for x in diff.splitlines()
                                         if x[:1] in "+-" and not x.startswith(("+++", "---"))),
                    "diff": f"golden/real/prs/{pid}.diff", "clean": not expected, "expected": expected})
    return prs


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python golden/real/build_real.py <path-to-click-clone> golden")
    golden = Path(sys.argv[2])
    prs = build(Path(sys.argv[1]), golden / "real" / "prs")
    out = {"version": 1, "source": "pallets/click; pairs named by click itself (CHANGES.md / fix commit title)",
           "matching_rule": "same as labels_seeded.json; a problem counts as found if ANY of its ranges is matched",
           "reporting": "per-PR: each real PR is reported on its own (bug, found/missed, what the bot said); no recall "
                        "percentage for the real set (Nishant, 24 Oct 2026, REAL_PRS_REVIEW.md option A)",
           "prs": prs}
    (golden / "labels_real.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    for p in prs:
        print(f"{p['id']}: {p['changed_lines']} changed lines, {len({e['problem'] for e in p['expected']})} "
              f"problem(s), {len(p['expected'])} label range(s)")
