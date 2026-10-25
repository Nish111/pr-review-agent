"""SQLite schema for ingress and the queue (FAILURE_MATRIX_01_INGRESS.md; S3: one local store, no Redis).

The atomic claim for ingress F9 is a UNIQUE index: two writers racing on the same work key can't both win,
whatever the timing, because the database refuses the second insert.
"""

from __future__ import annotations

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS deliveries (            -- F8 check 1: one row per X-GitHub-Delivery
    delivery_id TEXT PRIMARY KEY,
    event TEXT NOT NULL,
    received_at TEXT NOT NULL,
    outcome TEXT NOT NULL                          -- accepted | ignored:<why> | duplicate-work | dead-letter
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    work_key TEXT NOT NULL UNIQUE,                 -- F8 check 2 + F9: repo#pr@sha, claimed atomically
    repo TEXT NOT NULL, pr_number INTEGER NOT NULL, head_sha TEXT NOT NULL,
    delivery_id TEXT NOT NULL, trigger TEXT NOT NULL,
    is_fork INTEGER NOT NULL DEFAULT 0,            -- F5
    untrusted_title TEXT NOT NULL DEFAULT '',      -- F4: carried, never interpreted here
    state TEXT NOT NULL DEFAULT 'queued',          -- queued | running | done | superseded | dead
    attempts INTEGER NOT NULL DEFAULT 0,           -- F14
    not_before REAL NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    last_error TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS jobs_pr ON jobs(repo, pr_number, state);
CREATE TABLE IF NOT EXISTS dead_letters (          -- F6, F14: kept for study and replay, never deleted
    id INTEGER PRIMARY KEY, kind TEXT NOT NULL, ref TEXT NOT NULL, reason TEXT NOT NULL,
    payload TEXT NOT NULL, created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS commands (              -- F17: /review commands, for the daily limit
    id INTEGER PRIMARY KEY, repo TEXT NOT NULL, pr_number INTEGER NOT NULL,
    author TEXT NOT NULL, day TEXT NOT NULL, outcome TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pushes (                -- F10: push timestamps per PR, to detect bursts
    repo TEXT NOT NULL, pr_number INTEGER NOT NULL, head_sha TEXT NOT NULL, at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (                -- F16 / F10: what the bot intends to say on GitHub (posted at M9)
    id INTEGER PRIMARY KEY, kind TEXT NOT NULL, repo TEXT NOT NULL, pr_number INTEGER NOT NULL,
    head_sha TEXT NOT NULL, text TEXT NOT NULL, created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events (                -- trace of every ingress decision (safe fields only, F15)
    id INTEGER PRIMARY KEY, at REAL NOT NULL, name TEXT NOT NULL, detail TEXT NOT NULL
);
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=10, isolation_level=None, check_same_thread=False)  # autocommit
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL") if path != ":memory:" else None
    conn.executescript(SCHEMA)
    return conn
