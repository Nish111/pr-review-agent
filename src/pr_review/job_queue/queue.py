"""Taking, finishing and failing jobs; draining the inbox; and the two recovery jobs.

Nothing here deletes anything: superseded and dead jobs stay in the table with their state.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterable
from pathlib import Path

MAX_ACTIVE = 2            # F13: reviews running at the same time
MAX_ATTEMPTS = 3          # F14
BACKOFF_S = (0, 30, 120)  # wait before attempt 1, 2, 3
ALERT_WAIT_S = 900        # F13: alert when the oldest queued job has waited longer than this


def take(conn: sqlite3.Connection, now: float, max_active: int = MAX_ACTIVE) -> sqlite3.Row | None:
    """Next queued job, oldest first, if fewer than max_active are running. Marks it running atomically.
    One worker process calls this (the count check is not race-safe across several workers)."""
    if conn.execute("SELECT COUNT(*) FROM jobs WHERE state='running'").fetchone()[0] >= max_active:
        return None
    row = conn.execute("SELECT * FROM jobs WHERE state='queued' AND not_before<=? ORDER BY created_at, id LIMIT 1",
                       (now,)).fetchone()
    if row is None:
        return None
    cur = conn.execute("UPDATE jobs SET state='running', attempts=attempts+1 WHERE id=? AND state='queued'",
                       (row["id"],))
    return conn.execute("SELECT * FROM jobs WHERE id=?", (row["id"],)).fetchone() if cur.rowcount == 1 else None


def oldest_waiting_s(conn: sqlite3.Connection, now: float) -> float:
    """F13 metric: seconds the oldest queued job has waited (0 when the queue is empty)."""
    t = conn.execute("SELECT MIN(created_at) FROM jobs WHERE state='queued'").fetchone()[0]
    return 0.0 if t is None else now - t


def is_superseded(conn: sqlite3.Connection, job_id: int) -> bool:
    """Checked by the worker before each expensive step (F10)."""
    return conn.execute("SELECT state FROM jobs WHERE id=?", (job_id,)).fetchone()["state"] == "superseded"


def complete(conn: sqlite3.Connection, job_id: int) -> None:
    conn.execute("UPDATE jobs SET state='done' WHERE id=? AND state='running'", (job_id,))


def fail(conn: sqlite3.Connection, job_id: int, error: str, now: float) -> str:
    """Retry with backoff; after MAX_ATTEMPTS the job is dead and a copy goes to dead_letters (F14)."""
    job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if job["attempts"] >= MAX_ATTEMPTS:
        conn.execute("UPDATE jobs SET state='dead', last_error=? WHERE id=?", (error[:500], job_id))
        conn.execute("INSERT INTO dead_letters (kind, ref, reason, payload, created_at) VALUES ('job',?,?,?,?)",
                     (job["work_key"], error[:300], json.dumps(dict(job)), now))
        return "dead"
    conn.execute("UPDATE jobs SET state='queued', last_error=?, not_before=? WHERE id=?",
                 (error[:500], now + BACKOFF_S[min(job["attempts"], len(BACKOFF_S) - 1)], job_id))
    return "retry"


def drain_inbox(inbox: Path, ingest: Callable[[str, str, bytes], str]) -> int:
    """Replay every inbox line into ingest(). Safe to repeat: ingest drops deliveries it has seen (F12)."""
    if not inbox.is_file():
        return 0
    n = 0
    for line in inbox.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            if ingest(rec["delivery"], rec["event"], rec["body"].encode("utf-8")) != "duplicate-delivery":
                n += 1
    return n


def sweep(conn: sqlite3.Connection, open_prs: Iterable[dict], claim: Callable[..., str], now: float) -> list[str]:
    """F11 backstop: every open, non-draft PR whose head commit has no job gets one.
    open_prs: dicts with repo, number, head_sha, draft, title (from the GitHub API, injected)."""
    added = []
    for pr in open_prs:
        if pr.get("draft"):
            continue
        key = f"{pr['repo']}#{pr['number']}@{pr['head_sha']}"
        if conn.execute("SELECT 1 FROM jobs WHERE work_key=?", (key,)).fetchone():
            continue
        if claim(pr["repo"], int(pr["number"]), pr["head_sha"], f"sweep:{key}", "sweep", False,
                 pr.get("title", ""), now) == "accepted":
            added.append(key)
    return added


def redeliver_failed(failed_ids: Iterable[str], redeliver: Callable[[str], None]) -> int:
    """F11: GitHub's recommended pattern (Nishant's docs check): ask GitHub to resend each failed delivery.
    Resent deliveries keep their X-GitHub-Delivery id, so ingest drops any that did arrive after all."""
    n = 0
    for d in failed_ids:
        redeliver(d)
        n += 1
    return n
