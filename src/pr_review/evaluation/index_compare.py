"""Before/after numbers for matrices 02 and 03: the html's index design (ingestion/baseline.py) vs ours.

Y1 (exact names): every function, method and class name defined once in the tree's Python files is searched for;
a hit = the chunk containing its definition line is in the top 5. X2-X4 (freshness) use small throwaway trees in an
OS temp folder (removed by Python when the run ends); nothing in the repo is touched.
"""

from __future__ import annotations

import ast
import sqlite3
import tempfile
from collections import Counter
from pathlib import Path

from pr_review.embedder import HashEmbedder
from pr_review.ingestion.baseline import BaselineIndex
from pr_review.ingestion.index import Index
from pr_review.ingestion.walker import walk
from pr_review.retrieval import search

TOP = 5


def definitions(tree: Path) -> list[tuple[str, str, int]]:
    """(name, path, line) for names defined exactly once across the tree's Python files (dunders skipped)."""
    seen: dict[str, list[tuple[str, int]]] = {}
    for path, data in walk(tree, Counter()):
        if not path.endswith(".py"):
            continue
        try:
            mod = ast.parse(data.decode("utf-8", "replace"))
        except SyntaxError:
            continue
        for node in ast.walk(mod):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                seen.setdefault(node.name, []).append((path, node.lineno))
    return sorted((n, locs[0][0], locs[0][1]) for n, locs in seen.items()
                  if len(locs) == 1 and not (n.startswith("__") and n.endswith("__")))


def y1(tree: Path) -> dict:
    conn = sqlite3.connect(":memory:", isolation_level=None)
    ours, base = Index(conn), BaselineIndex(conn)
    ours.refresh("repo", tree, "base")
    base.refresh("repo", tree)
    defs = definitions(tree)
    o_hit = b_hit = 0
    misses: dict[str, list[str]] = {"ours": [], "baseline": []}
    for name, path, line in defs:
        o = [(h.path, h.start_line, h.end_line) for h in search(ours, "repo", name, k=TOP).hits]
        b = base.search("repo", name, k=TOP)
        o_ok = any(p == path and s <= line <= e for p, s, e in o)
        b_ok = any(p == path and s <= line <= e for p, s, e in b)
        o_hit += o_ok
        b_hit += b_ok
        if not o_ok:
            misses["ours"].append(name)
        if not b_ok:
            misses["baseline"].append(name)
    n = len(defs)
    return {"names": n, "baseline_hits": b_hit, "ours_hits": o_hit,
            "baseline_rate": round(b_hit / n, 3) if n else None, "ours_rate": round(o_hit / n, 3) if n else None,
            "ours_misses_sample": misses["ours"][:15], "baseline_misses_sample": misses["baseline"][:15]}


class _Counting(HashEmbedder):
    def __init__(self):
        super().__init__(32)
        self.calls = 0

    def embed(self, texts):
        self.calls += len(texts)
        return super().embed(texts)


def _funcs(n: int, header: str = "") -> str:
    return header + "".join(f"def f{i}(x):\n    y = x + {i}\n    return y\n\n\n" for i in range(n))


def freshness() -> dict:
    with tempfile.TemporaryDirectory(prefix="pr_review_index_") as tmp:
        t = Path(tmp)
        (t / "big.txt").write_text("\n".join(f"line {i}" for i in range(700)))
        (t / "gone.txt").write_text("x\n" * 100)
        (t / "m.py").write_text(_funcs(40))
        emb = _Counting()
        ours = Index(sqlite3.connect(":memory:", isolation_level=None), emb)
        base = BaselineIndex(sqlite3.connect(":memory:"))
        ours.refresh("r", t, "c1")
        base.refresh("r", t)
        emb.calls = 0
        (t / "big.txt").write_text("\n".join(f"line {i}" for i in range(400)))     # X2: shrink 12 -> 7 chunks
        (t / "gone.txt").rename(t / "renamed.txt")                                 # X3: old path disappears
        (t / "m.py").write_text(_funcs(40, header="import os\n"))                  # X4: one line at the top
        ours.refresh("r", t, "c2")
        b = base.refresh("r", t)

        def stale(conn, table: str) -> int:
            return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE (path='big.txt' AND start_line>400) "
                                "OR path='gone.txt'").fetchone()[0]

        b_m = base.conn.execute("SELECT COUNT(*) FROM b_chunks WHERE path='m.py'").fetchone()[0]
        return {"X2_X3_ghost_chunks": {"want": 0, "baseline": stale(base.conn, "b_chunks"),
                                       "ours": stale(ours.conn, "chunks")},
                "X4_embeddings_after_one_line_edit": {"baseline": b["embedded"], "ours": emb.calls,
                                                      "note": f"baseline re-embeds all {b_m} chunks of every changed "
                                                              "file (here m.py, big.txt and renamed.txt)"}}


def run(tree: Path) -> dict:
    return {"tree": tree.as_posix(), "Y1_exact_name_top5": y1(tree), **freshness()}
