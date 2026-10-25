"""The html's index design, kept runnable as the 'before' for matrix 02/03 numbers (pr-review-agent.html §2.3, §3.5).

Faithful, including its gaps: fixed 60-line chunks numbered by position, upsert on (repo, path, chunk_index),
a whole file re-embedded when its hash changes, nothing removed when a file shrinks or disappears, and keyword
search with English stemming (FTS5 'porter' stands in for Postgres to_tsvector('english')).
Used only by `python -m pr_review index-compare`; never in the real path.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections import Counter
from pathlib import Path

from pr_review.ingestion.text import split_lines
from pr_review.ingestion.walker import walk

CHUNK = 60

SCHEMA = """
CREATE TABLE IF NOT EXISTS b_files (repo TEXT, path TEXT, sha256 TEXT, PRIMARY KEY (repo, path));
CREATE TABLE IF NOT EXISTS b_chunks (id INTEGER PRIMARY KEY, repo TEXT, path TEXT, chunk_index INTEGER,
    start_line INTEGER, end_line INTEGER, text TEXT, UNIQUE (repo, path, chunk_index));
CREATE VIRTUAL TABLE IF NOT EXISTS b_fts USING fts5(text, tokenize = 'porter unicode61');
"""


class BaselineIndex:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        conn.executescript(SCHEMA)

    def refresh(self, repo: str, root: Path) -> dict:
        embedded = 0
        for path, data in walk(root, Counter()):
            digest = hashlib.sha256(data).hexdigest()
            row = self.conn.execute("SELECT sha256 FROM b_files WHERE repo=? AND path=?", (repo, path)).fetchone()
            if row and row[0] == digest:
                continue
            lines = split_lines(data.decode("utf-8", errors="replace"))
            for i, s in enumerate(range(0, len(lines), CHUNK)):
                text = "\n".join(lines[s:s + CHUNK])
                embedded += 1                                            # every chunk of a changed file
                self.conn.execute(
                    "INSERT INTO b_chunks (repo, path, chunk_index, start_line, end_line, text) VALUES (?,?,?,?,?,?) "
                    "ON CONFLICT (repo, path, chunk_index) DO UPDATE SET start_line=excluded.start_line, "
                    "end_line=excluded.end_line, text=excluded.text",
                    (repo, path, i, s + 1, min(s + CHUNK, len(lines)), text))
                cid = self.conn.execute("SELECT id FROM b_chunks WHERE repo=? AND path=? AND chunk_index=?",
                                        (repo, path, i)).fetchone()[0]
                self.conn.execute("DELETE FROM b_fts WHERE rowid=?", (cid,))
                self.conn.execute("INSERT INTO b_fts (rowid, text) VALUES (?, ?)", (cid, text))
            self.conn.execute("INSERT OR REPLACE INTO b_files VALUES (?, ?, ?)", (repo, path, digest))
        return {"embedded": embedded}

    def chunks_for(self, repo: str, path: str) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM b_chunks WHERE repo=? AND path=?", (repo, path)).fetchone()[0]

    def search(self, repo: str, name: str, k: int = 5) -> list[tuple[str, int, int]]:
        q = '"' + name.replace('"', '""') + '"'
        rows = self.conn.execute(
            "SELECT c.path, c.start_line, c.end_line FROM b_fts JOIN b_chunks c ON c.id = b_fts.rowid "
            "WHERE b_fts MATCH ? AND c.repo=? ORDER BY bm25(b_fts) LIMIT ?", (q, repo, k)).fetchall()
        return [tuple(r) for r in rows]
