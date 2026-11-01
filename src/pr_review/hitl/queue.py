"""Approval queue in the one SQLite file (S3). States: pending -> approved | rejected; approved -> disputed.
Fingerprints make re-runs idempotent (G11); disputes become labels for the next calibration (G9).
The bot never approves a PR or merges (invariant): 'approved' here means a human approved one COMMENT."""

from __future__ import annotations

import hashlib
import sqlite3
import time
from collections.abc import Callable

SCHEMA = """
CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY, fingerprint TEXT NOT NULL UNIQUE, work_key TEXT NOT NULL, file TEXT NOT NULL,
    line_start INTEGER NOT NULL, line_end INTEGER NOT NULL, text TEXT NOT NULL, score REAL,
    state TEXT NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','approved','rejected','disputed')),
    created_at REAL NOT NULL, decided_at REAL, decided_by TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS calibration_labels (
    fingerprint TEXT PRIMARY KEY, right INTEGER NOT NULL, source TEXT NOT NULL, created_at REAL NOT NULL);
"""
STALE_S = 2 * 86400


def fingerprint(work_key: str, file: str, line_start: int, line_end: int, category_group: str) -> str:
    raw = f"{work_key}|{file}|{line_start}-{line_end}|{category_group}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class ApprovalQueue:
    def __init__(self, conn: sqlite3.Connection, clock: Callable[[], float] = time.time):
        self.conn, self.clock = conn, clock
        conn.executescript(SCHEMA)

    def enqueue(self, work_key: str, file: str, line_start: int, line_end: int, text: str, score: float | None,
                category_group: str) -> bool:
        """False if this comment is already queued or decided (G11: a re-run adds nothing)."""
        fp = fingerprint(work_key, file, line_start, line_end, category_group)
        try:
            self.conn.execute("INSERT INTO approvals (fingerprint, work_key, file, line_start, line_end, text, score, "
                              "created_at) VALUES (?,?,?,?,?,?,?,?)",
                              (fp, work_key, file, line_start, line_end, text, score, self.clock()))
            return True
        except sqlite3.IntegrityError:
            return False

    def pending(self) -> list[dict]:
        """G8: oldest first, with age in hours and a stale flag."""
        now = self.clock()
        rows = self.conn.execute("SELECT id, work_key, file, line_start, line_end, text, score, created_at "
                                 "FROM approvals WHERE state='pending' ORDER BY created_at, id").fetchall()
        return [{"id": r[0], "work_key": r[1], "where": f"{r[2]}:{r[3]}-{r[4]}", "text": r[5], "score": r[6],
                 "age_h": round((now - r[7]) / 3600, 1), "stale": now - r[7] > STALE_S} for r in rows]

    def _decide(self, item_id: int, frm: str, to: str, who: str, note: str) -> None:
        cur = self.conn.execute("UPDATE approvals SET state=?, decided_at=?, decided_by=?, note=? "
                                "WHERE id=? AND state=?", (to, self.clock(), who, note, item_id, frm))
        if cur.rowcount != 1:
            raise ValueError(f"item {item_id} is not '{frm}'")

    def approve(self, item_id: int, who: str, note: str = "") -> None:
        self._decide(item_id, "pending", "approved", who, note)
        self._label(item_id, True, "approved")

    def reject(self, item_id: int, who: str, note: str = "") -> None:
        self._decide(item_id, "pending", "rejected", who, note)
        self._label(item_id, False, "rejected")

    def dispute(self, item_id: int, who: str, note: str) -> None:
        """G9: someone says an approved/posted comment was wrong; the label flips for the next calibration."""
        self._decide(item_id, "approved", "disputed", who, note)
        self._label(item_id, False, "disputed")

    def _label(self, item_id: int, right: bool, source: str) -> None:
        fp = self.conn.execute("SELECT fingerprint FROM approvals WHERE id=?", (item_id,)).fetchone()[0]
        self.conn.execute("INSERT OR REPLACE INTO calibration_labels VALUES (?, ?, ?, ?)", (fp, int(right), source,
                                                                                           self.clock()))
