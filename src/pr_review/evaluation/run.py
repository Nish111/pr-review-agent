"""Run one rung over the golden set and score it. Output: printed tables + eval/results/rung<N>.json."""

from __future__ import annotations

import json
import subprocess
import tarfile
from io import BytesIO
from pathlib import Path

from pr_review.evaluation.golden import changed_lines
from pr_review.evaluation.score import PRScore, matches, score_pr, totals
from pr_review.static_checks import RULES, review_tree
from pr_review.static_checks.ruff_check import ruff_version


def _click_tree(click_repo: Path, commit: str, workdir: Path, name: str | None = None) -> Path:
    """click at `commit` (any git revision, e.g. "2468b70^" for its parent), extracted once into eval/workdir/
    (gitignored, kept, never deleted). `name` overrides the folder name."""
    dest = workdir / (name or f"click-{commit}")
    if not dest.exists():
        data = subprocess.run(["git", "-C", str(click_repo), "archive", commit], capture_output=True,
                              check=True, timeout=120).stdout
        with tarfile.open(fileobj=BytesIO(data)) as tar:
            try:
                tar.extractall(dest, filter="data")   # safe extraction (Python 3.10.12+ / 3.11.4+)
            except TypeError:
                tar.extractall(dest)                  # older Python: archive comes from click's own git
    return dest


def _fmt(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.2f}"


def rung1(root: Path, click_repo: Path | None) -> dict:
    seeded = json.loads((root / "golden/labels_seeded.json").read_text(encoding="utf-8"))
    real = json.loads((root / "golden/labels_real.json").read_text(encoding="utf-8"))
    rows, scores = [], []
    for pr in seeded["prs"]:
        tree = root / "golden/seeded/head" / pr["id"]
        if not tree.is_dir():
            raise SystemExit(f"{tree} missing: run `python golden/seeded/build.py` first")
        changed = changed_lines((root / pr["diff"]).read_text(encoding="utf-8"))
        fs = review_tree(tree, changed)
        s = score_pr(pr, fs)
        scores.append(s)
        rows.append(_row(pr, s, fs))
    real_rows = []
    if click_repo is not None:
        workdir = root / "eval/workdir"
        workdir.mkdir(parents=True, exist_ok=True)
        for pr in real["prs"]:
            tree = _click_tree(click_repo, pr["intro_commit"], workdir)
            changed = changed_lines((root / pr["diff"]).read_text(encoding="utf-8"))
            fs = review_tree(tree, changed)
            real_rows.append(_row(pr, score_pr(pr, fs), fs))
    return {"rung": 1, "tool": ruff_version(), "rules": list(RULES), "seeded": {"totals": totals(scores),
            "prs": rows}, "real": {"reporting": "per-PR", "prs": real_rows,
                                    "skipped": click_repo is None}}


def _row(pr: dict, s: PRScore, fs: list) -> dict:
    labels = pr.get("expected", [])
    return {"id": pr["id"], "clean": s.clean, "problems": sorted(s.problems), "found": sorted(s.found),
            "findings": [{"file": f.location.file_path, "lines": [f.location.line_start, f.location.line_end],
                          "rule": f.category, "message": f.summary,
                          "matched": any(matches(f, lab) for lab in labels)} for f in fs],
            "true_positives": s.true_positives}


def print_report(res: dict) -> None:
    t = res["seeded"]["totals"]
    if res["rung"] == 1:
        print(f"Rung 1 ({res['tool']}, rules {','.join(res['rules'])})")
    else:
        print(f"Rung {res['rung']} ({res['provider']} / {res['model']}, "
              f"prompt {res['prompt']} sha {res['prompt_sha']})")
        if str(res["rung"]).startswith("3"):
            print(f"  arm: {res['arm']}   embedder: {res['embedder']}")
        for tr in res.get("trace", []):
            if "specialists" in tr:
                sp = "  ".join(f"{k}={'ok' if v['ok'] else 'FAILED'}{'(c)' if v['cached'] else ''}"
                               f"/{v['findings']}" for k, v in tr["specialists"].items())
                ret = tr.get("retrieval", {})
                print(f"  {tr['pr']:4} {'PARTIAL ' if tr['partial'] else ''}{sp}  merged={len(tr['merges'])}"
                      + (f"  search={ret.get('mode')} chunks={len(ret.get('hits', []))}" if ret else ""))
                continue
            bad = tr.get("error") or tr.get("parse_error")
            print(f"  call {tr['pr']:4} sent={tr.get('sent')} cached={tr.get('cached')} "
                  f"tokens~{tr.get('est_tokens')} {tr.get('latency_s')}s dropped={len(tr.get('dropped', []))}"
                  + (f"  PROBLEM: {bad[:80]}" if bad else ""))
        if res.get("stopped"):
            print(f"  STOPPED: {res['stopped']}  (re-run the same command after the quota resets; "
                  "finished PRs are cached)")
    print(f"SEEDED  precision {_fmt(t['precision'])} ({t['true_positives']}/{t['findings']} right)   "
          f"recall {_fmt(t['recall'])} ({t['problems_found']}/{t['problems']} planted problems found)   "
          f"false alarms on clean PRs: {t['false_alarms_on_clean_prs']}")
    for r in res["seeded"]["prs"]:
        mark = "clean" if r["clean"] else ("FOUND" if r["found"] else "missed")
        print(f"  {r['id']:4} {mark:6} findings={len(r['findings'])}")
        for f in r["findings"]:
            tag = "match" if f["matched"] else "NO MATCH, needs your check"
            print(f"         {f['file']}:{f['lines'][0]} {f['rule']} [{tag}] {f['message'][:60]}")
    if res["real"]["skipped"]:
        print("REAL    skipped (pass --click <path-to-click-clone> to include the 5 click PRs)")
    else:
        print("REAL    per PR (no percentage, decision A):")
        for r in res["real"]["prs"]:
            print(f"  {r['id']:4} found {len(r['found'])}/{len(r['problems'])} problem(s), "
                  f"findings={len(r['findings'])}")
            for f in r["findings"]:
                print(f"         {f['file']}:{f['lines'][0]} {f['rule']} {f['message'][:70]}")
