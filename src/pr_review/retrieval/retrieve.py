"""Hybrid retrieval over the index (matrix 03). Defences by tag: R1 whole-identifier keyword lane; R2 only quoted
identifiers ever reach FTS5; R3 names from changed lines, no keywords/built-ins, rarest first, max 20; R4 chunks the
diff already shows are dropped; R5 RRF merge + minimum similarity for vector-only hits; R6 token budget, not a fixed k;
R7 index commit must equal the PR base commit; R8/R9 mode flag, never silent; R10 chunks are returned as data with
their location (the prompt layer quotes them); R11 the result is the allowed evidence list."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field

from pr_review.embedder import Embedder
from pr_review.ingestion.index import Index, pack
from pr_review.ingestion.text import STOP, identifiers, parts

RRF_K = 60
MAX_NAMES = 20
LANE_DEPTH = 30                 # candidates taken from each lane before merging
MIN_SIMILARITY = 0.5            # R5: cosine; vectors are normalised, so L2 distance <= 1.0
BUDGET_TOKENS = 1500            # R6: Claude's suggestion in matrix 03
CHARS_PER_TOKEN = 4             # same rough estimate as specialists/single.py

_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@")


@dataclass(frozen=True)
class Hit:
    chunk_id: int
    path: str
    start_line: int
    end_line: int
    symbol: str
    text: str
    lanes: tuple[str, ...]      # which lane(s) found it: keyword, vector
    score: float

    @property
    def tokens(self) -> int:
        return max(1, len(self.text) // CHARS_PER_TOKEN)


@dataclass
class Result:
    mode: str                   # hybrid | keyword-only | no-index | stale
    hits: list[Hit] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    dropped_in_diff: int = 0
    didnt_fit: list[str] = field(default_factory=list)
    tokens_used: int = 0
    note: str = ""


def _fts_query(names: list[str]) -> str:
    """R2: identifiers only, each one quoted; nothing else from the diff reaches the FTS5 query language."""
    return " OR ".join('"' + n.lower().replace('"', '""') + '"' for n in names)


def _keyword(conn: sqlite3.Connection, repo: str, names: list[str], extra: list[str] | None = None) -> list[int]:
    """R1: chunks that DEFINE one of the names come first (exact case), then FTS5 matches on whole names.
    `extra` terms (name parts, for free-text search) join the FTS query but never the definition lookup."""
    if not names:
        return []
    defs: list[int] = []
    for n in names:
        rows = conn.execute("SELECT id FROM chunks WHERE repo=? AND instr(' ' || defines || ' ', ?) > 0 ORDER BY id",
                            (repo, f" {n} "))
        defs += [r[0] for r in rows if r[0] not in defs]
    rows = conn.execute(
        "SELECT c.id FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid "
        "WHERE chunks_fts MATCH ? AND c.repo=? ORDER BY bm25(chunks_fts) LIMIT ?",
        ("idents : (" + _fts_query(names + (extra or [])) + ")", repo, LANE_DEPTH)).fetchall()
    return (defs + [r[0] for r in rows if r[0] not in defs])[:LANE_DEPTH]


def _vector(conn: sqlite3.Connection, repo: str, embedder: Embedder, text: str) -> list[int]:
    v = pack(embedder.embed([text])[0])
    rows = conn.execute("SELECT rowid, distance FROM chunks_vec WHERE embedding MATCH ? AND k = ?",
                        (v, LANE_DEPTH * 3)).fetchall()
    max_dist = (2 - 2 * MIN_SIMILARITY) ** 0.5
    ids = [r[0] for r in rows if r[1] <= max_dist]
    if not ids:
        return []
    marks = ",".join("?" * len(ids))
    in_repo = {r[0] for r in conn.execute(f"SELECT id FROM chunks WHERE repo=? AND id IN ({marks})", (repo, *ids))}
    return [i for i in ids if i in in_repo][:LANE_DEPTH]


def _rrf(lanes: dict[str, list[int]]) -> list[tuple[int, float, tuple[str, ...]]]:
    score: dict[int, float] = {}
    found: dict[int, list[str]] = {}
    for lane, ids in lanes.items():
        for rank, cid in enumerate(ids, 1):
            score[cid] = score.get(cid, 0.0) + 1.0 / (RRF_K + rank)
            found.setdefault(cid, []).append(lane)
    return sorted(((c, s, tuple(found[c])) for c, s in score.items()), key=lambda x: (-x[1], x[0]))


def _hits(conn: sqlite3.Connection, merged: list[tuple[int, float, tuple[str, ...]]]) -> list[Hit]:
    out = []
    for cid, s, lanes in merged:
        r = conn.execute("SELECT path, start_line, end_line, symbol, text FROM chunks WHERE id=?", (cid,)).fetchone()
        out.append(Hit(cid, r[0], r[1], r[2], r[3], r[4], lanes, round(s, 5)))
    return out


def _mode(index: Index, repo: str, embedder: Embedder | None) -> str:
    if index.commit_of(repo) is None:
        return "no-index"
    return "hybrid" if embedder is not None and index.vec else "keyword-only"


def _code_like(conn: sqlite3.Connection, repo: str, word: str) -> bool:
    """R3 for free-text queries: a word goes to the keyword lane only if it looks like code (snake_case, camelCase,
    digits) or something in the repo is defined with that name. Plain English words go to the vector lane only."""
    if "_" in word or any(c.isdigit() for c in word) or (word[1:] != word[1:].lower() and word != word.upper()):
        return True
    return conn.execute("SELECT 1 FROM chunks WHERE repo=? AND instr(' ' || defines || ' ', ?) > 0 LIMIT 1",
                        (repo, f" {word} ")).fetchone() is not None


def search(index: Index, repo: str, query: str, k: int = 5) -> Result:
    """Free-text search for the CLI demo: `python -m pr_review search "verify_token"`."""
    mode = _mode(index, repo, index.embedder)
    if mode == "no-index":
        return Result(mode, note=f"no index for {repo}; run `python -m pr_review index` first")
    names = [n for n in identifiers(query) if n not in STOP and len(n) >= 3 and _code_like(index.conn, repo, n)]
    extra = [p for n in names for p in parts(n) if len(parts(n)) > 1]
    lanes = {"keyword": _keyword(index.conn, repo, names, extra)}
    if mode == "hybrid":
        lanes["vector"] = _vector(index.conn, repo, index.embedder, query)
    return Result(mode, hits=_hits(index.conn, _rrf(lanes))[:k], names=names)


def _diff_parts(diff: str) -> tuple[dict[str, list[tuple[int, int]]], str, list[str]]:
    """Base-side changed line ranges per file, the changed text, and names in changed lines (R3, R4)."""
    ranges: dict[str, list[tuple[int, int]]] = {}
    changed_text: list[str] = []
    path = None
    for raw in diff.splitlines():
        if raw.startswith("--- "):
            src = raw[4:].strip()
            path = None if src == "/dev/null" else src.removeprefix("a/")
        elif raw.startswith("+++ "):
            continue
        elif raw.startswith("@@"):
            m = _HUNK.match(raw)
            if m and path:
                start, count = int(m.group(1)), int(m.group(2) or 1)
                ranges.setdefault(path, []).append((start, start + max(count, 1) - 1))
        elif raw[:1] in "+-":
            changed_text.append(raw[1:])
    text = "\n".join(changed_text)
    return ranges, text, identifiers(text)


def _rarest(conn: sqlite3.Connection, repo: str, names: list[str]) -> list[str]:
    keep = [n for n in names if n not in STOP and len(n) >= 3 and _code_like(conn, repo, n)]
    freq = {}
    for n in keep:
        freq[n] = conn.execute(
            "SELECT COUNT(*) FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid WHERE chunks_fts MATCH ? "
            "AND c.repo=?", ("idents : " + _fts_query([n]), repo)).fetchone()[0]
    found = [n for n in keep if freq[n] > 0]                      # a brand-new name matches nothing; drop it
    return sorted(found, key=lambda n: (freq[n], keep.index(n)))[:MAX_NAMES]


def for_diff(index: Index, repo: str, diff: str, base_commit: str, budget_tokens: int = BUDGET_TOKENS) -> Result:
    """Context for one PR. The index must be at the PR's base commit (R7); refresh it first if not."""
    mode = _mode(index, repo, index.embedder)
    if mode == "no-index":
        return Result(mode, note="no index: review runs on the diff alone")
    at = index.commit_of(repo)
    if at != base_commit:
        return Result("stale", note=f"index is at {at}, PR base is {base_commit}: refresh before retrieving")
    ranges, changed, names = _diff_parts(diff)
    names = _rarest(index.conn, repo, names)
    lanes = {"keyword": _keyword(index.conn, repo, names)}
    if mode == "hybrid" and changed.strip():
        lanes["vector"] = _vector(index.conn, repo, index.embedder, changed)
    res = Result(mode, names=names)
    for h in _hits(index.conn, _rrf(lanes)):
        if any(h.path == p and h.start_line <= hi and lo <= h.end_line for p, rs in ranges.items() for lo, hi in rs):
            res.dropped_in_diff += 1                              # R4: the diff already shows it
        elif res.tokens_used + h.tokens <= budget_tokens:
            res.hits.append(h)
            res.tokens_used += h.tokens
        else:
            res.didnt_fit.append(f"{h.path}:{h.start_line}-{h.end_line}")   # R6: listed, not lost silently
    return res
