"""Process one review job end to end. Pure orchestration of parts built and tested in M4-M8; GitHub and the model are
injected, so the whole path runs in tests with fakes."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from pr_review import config
from pr_review.aggregator import features, group_findings
from pr_review.contracts import Severity
from pr_review.evaluation.golden import changed_lines
from pr_review.hitl import ApprovalQueue
from pr_review.hitl.queue import fingerprint
from pr_review.llm_client import last_usage
from pr_review.orchestrator import SPECIALISTS, TokenBucket, review_pr
from pr_review.orchestrator.specialists import REVIEW_BUDGET

ROOT = Path(__file__).resolve().parents[3]
POSTED = "CREATE TABLE IF NOT EXISTS posted (fingerprint TEXT PRIMARY KEY, work_key TEXT NOT NULL, at REAL NOT NULL)"


def _event(conn: sqlite3.Connection, now: float, name: str, detail: dict) -> None:
    conn.execute("INSERT INTO events (at, name, detail) VALUES (?, ?, ?)",
                 (now, name, json.dumps(detail, sort_keys=True)))


def _rows(fs) -> list[dict]:
    return [{"file": f.location.file_path, "lines": [f.location.line_start, f.location.line_end], "rule": f.category,
             "message": f.summary, "specialist": f.agent_type.value, "confidence": f.confidence,
             "severity": f.severity.value, "rationale": f.rationale, "suggestion": f.suggestion} for f in fs]


def _comment_body(posted: list[tuple], queued: int) -> str:
    lines = ["**PR review bot** · automated comments only; it never approves or merges.", ""]
    for g, score in posted:
        lead = g.lead
        where = f"{lead['file']}:{lead['lines'][0]}-{lead['lines'][1]}"
        lines += [f"- **{lead['severity']} · {lead['message']}** (`{where}`)",
                  f"  {lead['rationale']}", f"  *Suggestion:* {lead['suggestion']}",
                  f"  <sub>{lead['specialist']} reviewer"
                  + (f" + {', '.join(sorted({f['specialist'] for f in g.supporting}))}" if g.supporting else "")
                  + f" · calibrated score {score:.2f}</sub>", ""]
    if queued:
        lines.append(f"_{queued} more comment(s) are waiting for a human to approve._")
    return "\n".join(lines)


def process(conn: sqlite3.Connection, job: sqlite3.Row, gh, complete, now: float,
            bucket: TokenBucket | None = None) -> dict:
    repo, number, sha, key = job["repo"], job["pr_number"], job["head_sha"], job["work_key"]
    conn.execute(POSTED)
    queue = ApprovalQueue(conn, clock=lambda: now)
    gh.status(repo, sha, "pending", "Review running")
    pr = gh.pr(repo, number)
    diff = gh.pr_diff(repo, number)
    changed = changed_lines(diff)
    templates = {a: (ROOT / f"prompts/rung3_{a.value}.txt").read_text(encoding="utf-8") for a in SPECIALISTS}
    usage: list[dict] = []

    def ask(agent, prompt):
        try:
            raw = complete("groq", "openai/gpt-oss-120b", prompt)
            usage.append({"specialist": agent.value, **last_usage()})
            return {"ok": True, "raw": raw}
        except Exception as e:  # noqa: BLE001 - recorded as a failed specialist (W1), never an empty success
            return {"ok": False, "raw": "", "error": f"{type(e).__name__}: {str(e)[:200]}"}

    with tempfile.TemporaryDirectory(prefix="pr_review_live_") as tmp:   # the PR's changed files at head; removed after
        tree = Path(tmp)
        for path in changed:
            text = gh.file(repo, path, sha)
            if text is not None:
                (tree / path).parent.mkdir(parents=True, exist_ok=True)
                (tree / path).write_text(text, encoding="utf-8")
        rv = review_pr({"id": key, "title": pr.get("title", ""), "body": pr.get("body") or ""}, diff, tree, changed,
                       [], templates, ask, bucket or TokenBucket(), budget=REVIEW_BUDGET)
    cal = json.loads(config.CALIBRATION.read_text(encoding="utf-8")) if config.CALIBRATION.is_file() else None
    thr = config.threshold()
    posted, queued = [], 0
    for g in group_findings(key, _rows(rv["findings"])):
        lead = g.lead
        # a kind of comment the golden set never saw has no score, so it goes to a human (conservative; matrix 05 G5)
        score = cal["calibration_table"].get(" / ".join(features(g)), {}).get("score") if cal else None
        fp = fingerprint(key, lead["file"], lead["lines"][0], lead["lines"][1], " / ".join(features(g)))
        critical = lead["severity"] == Severity.CRITICAL.value
        if conn.execute("SELECT 1 FROM posted WHERE fingerprint=?", (fp,)).fetchone():
            continue                                              # G11: already posted for this commit
        if thr is not None and score is not None and score >= thr and not rv["partial"] and not critical:
            posted.append((g, score))
            conn.execute("INSERT OR IGNORE INTO posted VALUES (?, ?, ?)", (fp, key, now))
        else:
            text = f"[{lead['severity']}] {lead['message']} ({lead['specialist']}) — {lead['rationale']}"
            queued += queue.enqueue(key, lead["file"], lead["lines"][0], lead["lines"][1], text, score,
                                    " / ".join(features(g)))
    if posted or queued:
        gh.comment(repo, number, _comment_body(posted, queued))
    summary = {"work_key": key, "posted": len(posted), "queued": queued, "partial": rv["partial"],
               "completed": rv["completed"], "merges": len(rv["merges"]), "threshold": thr, "usage": usage,
               "dropped": {a.value: len(r.dropped) for a, r in rv["specialists"].items()},
               "errors": {a.value: r.error[:120] for a, r in rv["specialists"].items() if r.error}}
    _event(conn, now, "review.done", summary)
    gh.status(repo, sha, "success", f"{len(posted)} posted, {queued} waiting for approval"
              + (" (partial review)" if rv["partial"] else ""))
    return summary
