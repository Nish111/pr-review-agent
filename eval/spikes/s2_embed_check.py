"""Spike S2, run on Nishant's laptop: does the embedding model install and run fast enough on this CPU,
and does sqlite-vec load in this Python? Prints facts only; writes nothing except the model download cache.

    python eval/spikes/s2_embed_check.py                 # bge-small only (no downloaded code is run)
    python eval/spikes/s2_embed_check.py --allow-jina    # also jina (runs code from the jinaai model repo)
"""

from __future__ import annotations

import argparse
import platform
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JINA, BGE = "jinaai/jina-embeddings-v2-base-code", "BAAI/bge-small-en-v1.5"


def line(label: str, value: object) -> None:
    print(f"{label:<28} {value}")


def sample_chunks(n: int = 64) -> list[str]:
    """40-line blocks of the demo app's Python files, so the timing uses real code."""
    out = []
    for p in sorted((ROOT / "golden" / "seeded" / "base").rglob("*.py")):
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        out += ["\n".join(lines[i:i + 40]) for i in range(0, len(lines), 40)]
    return (out * (n // max(len(out), 1) + 1))[:n]


def check_model(name: str, remote_code: bool, chunks: list[str]) -> None:
    from sentence_transformers import SentenceTransformer
    t = time.perf_counter()
    model = SentenceTransformer(name, trust_remote_code=remote_code, device="cpu")
    line(f"{name} load (s)", round(time.perf_counter() - t, 1))
    rev = getattr(getattr(model[0], "auto_model", None), "config", None)
    line("  revision (pin this)", getattr(rev, "_commit_hash", "unknown"))
    model.encode(chunks[:4])                                         # warm-up, not timed
    t = time.perf_counter()
    vecs = model.encode(chunks, batch_size=16, normalize_embeddings=True)
    per = (time.perf_counter() - t) / len(chunks)
    line("  dimensions", vecs.shape[1])
    line("  seconds per chunk", round(per, 3))
    line("  est. click index (min)", round(per * 900 / 60, 1))       # ~900 chunks for click (rough)
    a, b, c = model.encode(["def add(a, b):\n    return a + b", "def plus(x, y):\n    return x + y",
                            "with open(path) as f:\n    data = json.load(f)"], normalize_embeddings=True)
    line("  similar vs unrelated", f"{float(a @ b):.2f} vs {float(a @ c):.2f} (first should be higher)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-jina", action="store_true", help="also test jina (runs code from its model repo)")
    args = ap.parse_args()
    line("python", sys.version.split()[0] + " " + platform.system())
    line("sqlite", sqlite3.sqlite_version)
    try:
        sqlite3.connect(":memory:").execute("CREATE VIRTUAL TABLE t USING fts5(x)")
        line("fts5", "ok")
    except sqlite3.Error as e:
        line("fts5", f"FAILED: {e}")
    try:
        import sqlite_vec
        conn = sqlite3.connect(":memory:")
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        line("sqlite-vec", "ok " + conn.execute("select vec_version()").fetchone()[0])
    except Exception as e:  # noqa: BLE001 - a spike reports every failure kind
        line("sqlite-vec", f"FAILED: {type(e).__name__}: {e}")
    try:
        import sentence_transformers
        line("sentence-transformers", sentence_transformers.__version__)
    except ImportError as e:
        line("sentence-transformers", f"NOT INSTALLED: {e}")
        return 1
    chunks = sample_chunks()
    for name, remote in ((BGE, False), (JINA, True)) if args.allow_jina else ((BGE, False),):
        try:
            check_model(name, remote, chunks)
        except Exception as e:  # noqa: BLE001
            line(name, f"FAILED: {type(e).__name__}: {str(e)[:300]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
