"""The code index in the one SQLite file (S3): files, chunks, keyword lane (FTS5) and vector lane (sqlite-vec).

Matrix 02 defences, by tag: I4/I3 in walker.py; I5 content hash; I6 replace-whole-file + remove missing paths;
I7 vectors cached by chunk-text hash; I8 model recorded and checked; I9 one transaction per file, hash written last;
I10 one run per repo; I11 bad bytes replaced and counted; I12 one line rule (text.split_lines).
Removing index rows is part of I6; nothing here touches files on disk.
"""

from __future__ import annotations

import hashlib
import sqlite3
import struct
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from pr_review.embedder import Embedder
from pr_review.ingestion.chunker import chunk_file
from pr_review.ingestion.text import ident_field
from pr_review.ingestion.walker import walk

STALE_LOCK_S = 3600

SCHEMA = """
CREATE TABLE IF NOT EXISTS index_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS index_lock (repo TEXT PRIMARY KEY, started_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS index_files (
    repo TEXT NOT NULL, path TEXT NOT NULL, sha256 TEXT NOT NULL, commit_sha TEXT NOT NULL,
    PRIMARY KEY (repo, path));
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY, repo TEXT NOT NULL, path TEXT NOT NULL, start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL, symbol TEXT NOT NULL, kind TEXT NOT NULL, text TEXT NOT NULL, text_hash TEXT NOT NULL,
    defines TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS chunks_by_path ON chunks (repo, path);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(idents, body, tokenize = "unicode61 tokenchars '_'");
CREATE TABLE IF NOT EXISTS vec_cache (model TEXT NOT NULL, text_hash TEXT NOT NULL, vector BLOB NOT NULL,
    PRIMARY KEY (model, text_hash));
"""


class ModelMismatch(RuntimeError):
    """I8: the index holds vectors from another model; adding to it would mix meanings."""


class AlreadyRunning(RuntimeError):
    """I10: another index run holds this repo."""


def load_vec(conn: sqlite3.Connection) -> bool:
    """Load sqlite-vec into this connection. False (keyword-only, R8) if the add-on or extension loading is missing."""
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except (ImportError, AttributeError, sqlite3.Error):
        return False


def pack(v: list[float]) -> bytes:
    return struct.pack(f"{len(v)}f", *v)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@dataclass
class Report:
    files_new: int = 0
    files_changed: int = 0
    files_unchanged: int = 0
    files_removed: int = 0
    chunks_written: int = 0
    embedded: int = 0
    vectors_reused: int = 0
    parse_fallbacks: list[str] = field(default_factory=list)
    decode_replaced: list[str] = field(default_factory=list)
    skipped: Counter = field(default_factory=Counter)
    seconds: float = 0.0
    vector_lane: bool = False


class Index:
    def __init__(self, conn: sqlite3.Connection, embedder: Embedder | None = None):
        self.conn, self.embedder = conn, embedder
        self.vec = load_vec(conn) if embedder else False
        conn.executescript(SCHEMA)
        if embedder:
            self._check_model()
            if self.vec:
                # Vectors are partitioned by repo, so one repo's search never sees another repo's chunks.
                # (Fixed 30 Oct 2026: the first table, chunks_vec, had no repo column; a k-nearest search over
                # all repos, filtered afterwards, returned different chunks for notes-svc once click was indexed.)
                conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec_repo USING vec0("
                             f"repo text partition key, embedding float[{embedder.dims}])")
                self._backfill_vectors()

    def _backfill_vectors(self) -> None:
        """Fill chunks_vec_repo from the vector cache for chunks indexed before it existed (no re-embedding)."""
        if self.conn.execute("SELECT COUNT(*) FROM chunks_vec_repo").fetchone()[0]:
            return
        rows = self.conn.execute("SELECT c.id, c.repo, v.vector FROM chunks c JOIN vec_cache v "
                                 "ON v.text_hash = c.text_hash AND v.model = ?", (self.embedder.name,)).fetchall()
        if rows:
            self.conn.execute("BEGIN IMMEDIATE")
            self.conn.executemany("INSERT INTO chunks_vec_repo (rowid, repo, embedding) VALUES (?, ?, ?)", rows)
            self.conn.execute("COMMIT")

    # ------------------------------------------------------------------ I8
    def _meta(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM index_meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def _check_model(self) -> None:
        name, dims = self._meta("model"), self._meta("dims")
        if name is None:
            self.conn.execute("INSERT INTO index_meta VALUES ('model', ?), ('dims', ?)",
                              (self.embedder.name, str(self.embedder.dims)))
        elif name != self.embedder.name or int(dims) != self.embedder.dims:
            raise ModelMismatch(f"index built with {name} ({dims} dims); asked to add {self.embedder.name} "
                                f"({self.embedder.dims} dims). A full rebuild is needed (new index file).")

    def commit_of(self, repo: str) -> str | None:
        return self._meta(f"commit:{repo}")

    # ------------------------------------------------------------------ I10
    def _lock(self, repo: str, now: float) -> None:
        self.conn.execute("DELETE FROM index_lock WHERE repo=? AND started_at<?", (repo, now - STALE_LOCK_S))
        try:
            self.conn.execute("INSERT INTO index_lock VALUES (?, ?)", (repo, now))
        except sqlite3.IntegrityError as e:
            raise AlreadyRunning(f"an index run for {repo} is already in progress") from e

    # ------------------------------------------------------------------ refresh
    def refresh(self, repo: str, root: Path, commit: str, stop_after: int | None = None) -> Report:
        """Bring the index for `repo` in line with the tree at `root` (= commit). Safe to re-run after a crash (I9).
        stop_after: test hook that simulates a crash after N changed files."""
        t0, rep = time.perf_counter(), Report(vector_lane=self.vec)
        self._lock(repo, time.time())
        try:
            known = dict(self.conn.execute("SELECT path, sha256 FROM index_files WHERE repo=?", (repo,)).fetchall())
            seen, done = set(), 0
            for path, data in walk(root, rep.skipped):
                seen.add(path)
                digest = _sha(data)
                if known.get(path) == digest:
                    rep.files_unchanged += 1
                    self.conn.execute("UPDATE index_files SET commit_sha=? WHERE repo=? AND path=?",
                                      (commit, repo, path))
                    continue
                if stop_after is not None and done >= stop_after:
                    raise RuntimeError("simulated crash (test hook)")
                self._write_file(repo, path, data, digest, commit, rep)
                rep.files_changed += path in known
                rep.files_new += path not in known
                done += 1
            for path in set(known) - seen:                           # I6: deleted or now-skipped files
                self.conn.execute("BEGIN IMMEDIATE")
                self._drop_chunks(repo, path)
                self.conn.execute("DELETE FROM index_files WHERE repo=? AND path=?", (repo, path))
                self.conn.execute("COMMIT")
                rep.files_removed += 1
            self.conn.execute("INSERT OR REPLACE INTO index_meta VALUES (?, ?)", (f"commit:{repo}", commit))
        finally:
            self.conn.execute("DELETE FROM index_lock WHERE repo=?", (repo,))
        rep.seconds = round(time.perf_counter() - t0, 2)
        return rep

    def _drop_chunks(self, repo: str, path: str) -> None:
        ids = [r[0] for r in self.conn.execute("SELECT id FROM chunks WHERE repo=? AND path=?", (repo, path))]
        for i in ids:
            self.conn.execute("DELETE FROM chunks_fts WHERE rowid=?", (i,))
            if self.vec:
                self.conn.execute("DELETE FROM chunks_vec_repo WHERE rowid=?", (i,))
        self.conn.execute("DELETE FROM chunks WHERE repo=? AND path=?", (repo, path))

    def _vectors(self, texts: list[str], rep: Report) -> list[bytes | None]:
        """I7: reuse a cached vector for any chunk text seen before; embed only the new texts."""
        if not self.embedder:
            return [None] * len(texts)
        hashes = [_sha(t.encode()) for t in texts]
        cached = {}
        for h in set(hashes):
            row = self.conn.execute("SELECT vector FROM vec_cache WHERE model=? AND text_hash=?",
                                    (self.embedder.name, h)).fetchone()
            if row:
                cached[h] = row[0]
        todo = [(h, t) for h, t in dict(zip(hashes, texts, strict=True)).items() if h not in cached]
        if todo:
            vecs = self.embedder.embed([t for _, t in todo])
            for (h, _), v in zip(todo, vecs, strict=True):
                cached[h] = pack(v)
                self.conn.execute("INSERT OR IGNORE INTO vec_cache VALUES (?, ?, ?)",
                                  (self.embedder.name, h, cached[h]))
        rep.embedded += len(todo)
        rep.vectors_reused += len(texts) - len(todo)
        return [cached[h] for h in hashes]

    def _write_file(self, repo: str, path: str, data: bytes, digest: str, commit: str, rep: Report) -> None:
        text = data.decode("utf-8", errors="replace")
        if "�" in text and b"\xef\xbf\xbd" not in data:
            rep.decode_replaced.append(path)                         # I11
        chunks, fallback = chunk_file(path, text)
        if fallback:
            rep.parse_fallbacks.append(path)                         # I2
        vectors = self._vectors([c.text for c in chunks], rep)       # before the transaction: may be slow
        self.conn.execute("BEGIN IMMEDIATE")                         # I9: the whole file or nothing
        try:
            self._drop_chunks(repo, path)                            # I6: replace, never upsert by position
            for c, v in zip(chunks, vectors, strict=True):
                cur = self.conn.execute(
                    "INSERT INTO chunks (repo, path, start_line, end_line, symbol, kind, text, text_hash, defines) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (repo, path, c.start_line, c.end_line, c.symbol, c.kind, c.text, _sha(c.text.encode()),
                     " ".join(c.defines)))
                cid = cur.lastrowid
                self.conn.execute("INSERT INTO chunks_fts (rowid, idents, body) VALUES (?, ?, ?)",
                                  (cid, ident_field(c.symbol + "\n" + c.text), c.text))
                if self.vec and v is not None:
                    self.conn.execute("INSERT INTO chunks_vec_repo (rowid, repo, embedding) VALUES (?, ?, ?)",
                                      (cid, repo, v))
            self.conn.execute("INSERT OR REPLACE INTO index_files VALUES (?, ?, ?, ?)",
                              (repo, path, digest, commit))          # last: marks the file as done
            self.conn.execute("COMMIT")
        except BaseException:
            if self.conn.in_transaction:
                self.conn.execute("ROLLBACK")
            raise
        rep.chunks_written += len(chunks)
