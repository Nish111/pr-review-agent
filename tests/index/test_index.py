"""Matrix 02 tests X1-X8 and matrix 03 tests Y2-Y6 (Y1 is the before/after number: `index-compare`)."""

import sqlite3
from collections import Counter
from pathlib import Path

import pytest

from pr_review.embedder import HashEmbedder
from pr_review.ingestion.baseline import BaselineIndex
from pr_review.ingestion.chunker import chunk_file
from pr_review.ingestion.index import AlreadyRunning, Index, ModelMismatch, load_vec
from pr_review.ingestion.text import ident_field, split_lines
from pr_review.ingestion.walker import walk
from pr_review.retrieval import for_diff, search

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "golden" / "seeded" / "base"
CLICKS = sorted((ROOT / "eval" / "workdir").glob("click-*"))


class CountingEmbedder(HashEmbedder):
    def __init__(self):
        super().__init__(32)
        self.calls = 0

    def embed(self, texts):
        self.calls += len(texts)
        return super().embed(texts)


def long_py(n_funcs: int, header: str = "") -> str:
    return header + "".join(f"def f{i}(x):\n    y = x + {i}\n    return y\n\n\n" for i in range(n_funcs))


def mk(tmp: Path, files: dict[str, str | bytes]) -> Path:
    for rel, content in files.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content if isinstance(content, bytes) else content.encode())
    return tmp


def index(embedder=None) -> Index:
    return Index(sqlite3.connect(":memory:", isolation_level=None), embedder)


# ---------------------------------------------------------------- X1: chunk text == file lines (I1, I12)
@pytest.mark.parametrize("tree", [DEMO, *CLICKS[:1]], ids=lambda p: p.name)
def test_x1_every_chunk_is_exactly_its_lines(tree):
    n = 0
    for path, data in walk(tree, Counter()):
        lines = split_lines(data.decode("utf-8", "replace"))
        chunks, _ = chunk_file(path, data.decode("utf-8", "replace"))
        covered = set()
        for c in chunks:
            assert c.text == "\n".join(lines[c.start_line - 1:c.end_line]), (path, c.start_line)
            covered.update(range(c.start_line, c.end_line + 1))
            n += 1
        assert all(i in covered for i, ln in enumerate(lines, 1) if ln.strip()), path   # nothing left out
    assert n > 0


def test_x1_functions_are_whole_and_long_ones_labelled():
    src = ("import os\n\n\ndef small():\n    return 1\n\n\n" + "def big():\n" + "    x = 1\n" * 130
           + "\n\nclass K:\n    a = 1\n")
    chunks, fallback = chunk_file("m.py", src)
    by = {(c.symbol, c.kind) for c in chunks}
    assert not fallback and ("small", "function") in by and ("K", "class") in by and ("<module>", "module") in by
    parts = [c for c in chunks if c.symbol == "big"]
    assert len(parts) > 1 and all(c.kind == "function-part" for c in parts)


def test_line_rule_matches_git_not_splitlines():
    text = "a\r\nb\x0cstill b\nc\n"
    assert split_lines(text) == ["a", "b\x0cstill b", "c"]          # str.splitlines would give 4 lines


# ---------------------------------------------------------------- X2/X3: no ghost chunks (I6)
def test_x2_x3_shrink_and_delete_leave_no_ghosts(tmp_path):
    tree = mk(tmp_path / "t", {"big.txt": "\n".join(f"line {i}" for i in range(700)), "gone.txt": "x\n" * 100})
    ours, base = index(), BaselineIndex(sqlite3.connect(":memory:"))
    ours.refresh("r", tree, "c1")
    base.refresh("r", tree)
    (tree / "big.txt").write_text("\n".join(f"line {i}" for i in range(400)))
    (tree / "gone.txt").rename(tree / "moved.txt")                    # = gone.txt deleted (test data only)
    ours.refresh("r", tree, "c2")
    base.refresh("r", tree)
    paths = {r[0] for r in ours.conn.execute("SELECT DISTINCT path FROM chunks")}
    assert paths == {"big.txt", "moved.txt"}
    assert max(r[0] for r in ours.conn.execute("SELECT end_line FROM chunks WHERE path='big.txt'")) == 400
    assert base.chunks_for("r", "gone.txt") > 0                       # the baseline keeps a deleted file
    assert base.conn.execute("SELECT MAX(end_line) FROM b_chunks WHERE path='big.txt'").fetchone()[0] == 700


# ---------------------------------------------------------------- X4: one-line edit (I7)
def test_x4_one_line_edit_reembeds_little(tmp_path):
    tree = mk(tmp_path / "t", {"m.py": long_py(40)})
    emb = CountingEmbedder()
    ours = index(emb)
    ours.refresh("r", tree, "c1")
    emb.calls = 0
    (tree / "m.py").write_text(long_py(40, header="import os\n"))
    rep = ours.refresh("r", tree, "c2")
    assert emb.calls == rep.embedded == 1 and rep.vectors_reused >= 40   # only the new module-level chunk
    base = BaselineIndex(sqlite3.connect(":memory:"))
    base.refresh("r", tree)
    (tree / "m.py").write_text(long_py(40, header="import os\nimport re\n"))
    assert base.refresh("r", tree)["embedded"] == 4                   # every 60-line chunk of the file


# ---------------------------------------------------------------- X5: junk and secrets (I3, I4)
def test_x5_junk_and_secrets_not_indexed(tmp_path):
    key = "-----BEGIN RSA PRIVATE KEY-----\nabc\n"
    tree = mk(tmp_path / "t", {"app.py": "def ok():\n    return 1\n", ".env": "TOKEN=abc\n", "deploy.key": "k",
                                "cfg.py": "AWS = 'AKIA" + "A" * 16 + "'\n", "id.txt": key, "logo.png": b"\x89PNG\0\0",
                                "uv.lock": "x", "node_modules/x/i.js": "var a", "big.txt": "a" * 300_000})
    skipped = Counter()
    assert [p for p, _ in walk(tree, skipped)] == ["app.py"]
    assert skipped == {"possible secret (name)": 2, "possible secret (content)": 2, "binary": 1,
                       "lock or generated file": 1, "over 200 KB": 1}
    assert "AKIA" not in str(skipped) and "PRIVATE" not in str(skipped)


# ---------------------------------------------------------------- X6: model change (I8)
def test_x6_model_change_refused():
    conn = sqlite3.connect(":memory:", isolation_level=None)
    Index(conn, HashEmbedder(32))
    with pytest.raises(ModelMismatch):
        Index(conn, HashEmbedder(64))


# ---------------------------------------------------------------- X7: crash and resume (I9), one run at a time (I10)
def test_x7_crash_then_resume(tmp_path):
    tree = mk(tmp_path / "t", {f"f{i}.py": f"def g{i}():\n    return {i}\n" for i in range(10)})
    emb = CountingEmbedder()
    ours = index(emb)
    with pytest.raises(RuntimeError, match="simulated crash"):
        ours.refresh("r", tree, "c1", stop_after=4)
    assert ours.conn.execute("SELECT COUNT(*) FROM index_files").fetchone()[0] == 4
    emb.calls = 0
    rep = ours.refresh("r", tree, "c1")
    assert rep.files_unchanged == 4 and rep.files_new == 6 and emb.calls == 6


def test_x7_second_run_refused(tmp_path):
    ours = index()
    ours.conn.execute("INSERT INTO index_lock VALUES ('r', ?)", (__import__("time").time(),))
    with pytest.raises(AlreadyRunning):
        ours.refresh("r", mk(tmp_path / "t", {"a.py": "x = 1\n"}), "c1")


# ---------------------------------------------------------------- X8: bad files still indexed (I2, I11)
def test_x8_syntax_error_and_bad_bytes(tmp_path):
    tree = mk(tmp_path / "t", {"broken.py": "def f(:\n    pass\n", "latin.txt": b"caf\xe9 au lait\n"})
    rep = index().refresh("r", tree, "c1")
    assert rep.parse_fallbacks == ["broken.py"] and rep.decode_replaced == ["latin.txt"] and rep.chunks_written == 2


# ---------------------------------------------------------------- retrieval (matrix 03)
def demo_index(embedder=None) -> Index:
    ix = index(embedder)
    ix.refresh("notes-svc", DEMO, "base")
    return ix


def test_r1_identifier_field_keeps_names_whole():
    assert ident_field("verify_token(x)") == "verify_token verify token x"
    assert ident_field("parseHTTPHeader") == "parsehttpheader parse http header"


def test_search_finds_definition_first():
    ix = demo_index()
    fns = [c for c in ix.conn.execute("SELECT symbol, path, start_line FROM chunks WHERE kind='function'")]
    sym, path, line = next(f for f in fns if "." not in f[0] and not f[0].startswith("_"))
    top = search(ix, "notes-svc", sym, k=5)
    assert top.mode == "keyword-only" and (top.hits[0].path, top.hits[0].start_line) == (path, line)


def test_y2_hostile_diff_never_breaks_the_query():
    ix = demo_index()
    diff = ('--- a/x.py\n+++ b/x.py\n@@ -1,2 +1,2 @@\n-a = "NEAR(" * AND - OR )\n'
            '+b = \'"*" NOT ^col: {x}\' AND NEAR\n')
    res = for_diff(ix, "notes-svc", diff, "base")
    assert res.mode == "keyword-only"                                 # no exception, a normal result


def test_y3_y4_budget_and_diff_overlap():
    ix = demo_index()
    diff = (ROOT / "golden" / "seeded" / "prs" / "S01.diff").read_text(encoding="utf-8")
    res = for_diff(ix, "notes-svc", diff, "base", budget_tokens=300)
    assert res.tokens_used <= 300 and res.names
    assert all(h.tokens for h in res.hits)
    big = for_diff(ix, "notes-svc", diff, "base", budget_tokens=100_000)
    assert len(big.hits) + big.dropped_in_diff >= len(res.hits) + res.dropped_in_diff
    assert big.didnt_fit == [] and (res.didnt_fit or len(res.hits) == len(big.hits))


def test_y5_keyword_only_when_no_vector_lane():
    ix = demo_index()                                                # no embedder
    assert search(ix, "notes-svc", "note").mode == "keyword-only"


@pytest.mark.skipif(not load_vec(sqlite3.connect(":memory:")), reason="sqlite-vec not installed")
def test_hybrid_mode_when_vector_lane_available():
    ix = demo_index(HashEmbedder(64))
    res = search(ix, "notes-svc", "create note title body")
    assert res.mode == "hybrid" and any("vector" in h.lanes for h in res.hits)


def test_y6_stale_index_refused_and_no_index_flagged():
    ix = demo_index()
    assert for_diff(ix, "notes-svc", "", "other-commit").mode == "stale"
    assert for_diff(ix, "unknown/repo", "", "base").mode == "no-index"
