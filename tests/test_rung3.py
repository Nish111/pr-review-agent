"""Matrix 04 tests Z1-Z7, plus an end-to-end rung 3 run on the seeded set with a fake model (no network)."""

import json
import re
import sqlite3
from pathlib import Path

import pytest

from pr_review.contracts import AgentType, Finding
from pr_review.embedder import HashEmbedder
from pr_review.evaluation.run_rung3 import rung3
from pr_review.llm_client import QuotaExhausted
from pr_review.orchestrator import TokenBucket, merge_duplicates, review_pr
from pr_review.orchestrator.specialists import related_block

ROOT = Path(__file__).resolve().parents[1]
HEADS = ROOT / "golden" / "seeded" / "head"
needs_heads = pytest.mark.skipif(not (HEADS / "S01").is_dir(), reason="run golden/seeded/build.py first")


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def finding(agent="security", path="a.py", lo=1, hi=1, cat="sql-injection", conf=0.9):
    return Finding.from_dict({"agent_type": agent, "severity": "high", "category": cat, "summary": "s",
                              "file_path": path, "line_start": lo, "line_end": hi, "confidence": conf,
                              "rationale": "r", "suggestion": "x",
                              "evidence": [{"file_path": path, "line_start": lo, "line_end": hi}]})


def answer(path, lo, hi, cat="sql-injection", ev=None):
    ev = ev or (path, lo, hi)
    return json.dumps({"findings": [{"severity": "high", "category": cat, "summary": "bad", "file_path": path,
                                     "line_start": lo, "line_end": hi, "confidence": 0.8, "rationale": "r",
                                     "suggestion": "s", "evidence": [{"file_path": ev[0], "line_start": ev[1],
                                                                      "line_end": ev[2]}]}]})


def tiny_pr(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\ny = 2\nz = x + y\n")
    diff = "--- a/a.py\n+++ b/a.py\n@@ -1,2 +1,3 @@\n x = 1\n y = 2\n+z = x + y\n"
    return {"id": "P1", "title": "t", "body": "b"}, diff, tmp_path, {"a.py": {3}}


TEMPLATES = {a: "{title}{body}{diff}{files}{context}" for a in AgentType if a.value in
             ("security", "quality", "tests", "docs")}


EMPTY = {k: '{"findings": []}' for k in ("quality", "tests", "docs")}


def asker(answers):
    def ask(agent, prompt):
        a = answers[agent.value]
        if isinstance(a, Exception):
            raise a
        return {"ok": True, "raw": a, "cached": False}
    return ask


# Z1: one specialist fails -> partial review with the others' findings
def test_z1_one_failure_gives_partial(tmp_path):
    pr, diff, tree, changed = tiny_pr(tmp_path)
    ask = asker({"security": answer("a.py", 3, 3), "quality": RuntimeError("boom"),
                 "tests": '{"findings": []}', "docs": '{"findings": []}'})
    with pytest.raises(RuntimeError):            # an unexpected error inside `ask` is not swallowed silently...
        review_pr(pr, diff, tree, changed, [], TEMPLATES, ask, TokenBucket())


def test_z1_failed_call_record_gives_partial(tmp_path):
    pr, diff, tree, changed = tiny_pr(tmp_path)

    def ask(agent, prompt):                      # ...the real Asker records call failures as ok=False instead
        if agent is AgentType.QUALITY:
            return {"ok": False, "raw": "", "error": "TimeoutError"}
        return {"ok": True, "raw": answer("a.py", 3, 3) if agent is AgentType.SECURITY else '{"findings": []}'}
    rv = review_pr(pr, diff, tree, changed, [], TEMPLATES, ask, TokenBucket())
    assert rv["partial"] and rv["completed"] == ["security", "tests", "docs"] and len(rv["findings"]) == 1
    assert rv["specialists"][AgentType.QUALITY].error == "TimeoutError"


# Z2: shared per-minute budget
def test_z2_never_more_than_budget_per_minute():
    clock = FakeClock()
    b = TokenBucket(8000, clock=clock, sleep=clock.sleep)
    starts = []
    for _ in range(8):
        b.reserve(3000)
        starts.append(clock.t)
    for t in starts:
        assert sum(3000 for s in starts if t - 60 < s <= t) <= 8000
    assert starts[2] >= 60                       # the third 3,000-token call had to wait for the window
    with pytest.raises(ValueError):
        b.reserve(9000)


# Z3: quota mid-PR stops the whole run cleanly (the resume is checked end to end below)
def test_z3_quota_stops_the_pr(tmp_path):
    pr, diff, tree, changed = tiny_pr(tmp_path)

    def ask(agent, prompt):
        if agent is AgentType.TESTS:
            raise QuotaExhausted("daily limit")
        return {"ok": True, "raw": '{"findings": []}'}
    with pytest.raises(QuotaExhausted):
        review_pr(pr, diff, tree, changed, [], TEMPLATES, ask, TokenBucket())


# Z4: exact duplicates merged
def test_z4_duplicates_merged():
    kept, merges = merge_duplicates([finding("security", conf=0.9), finding("quality", conf=0.6),
                                     finding("quality", cat="other")])
    assert len(kept) == 2 and len(merges) == 1 and merges[0]["dropped"].startswith("quality")


# Z5: ungrounded findings dropped (cites lines never shown)
def test_z5_ungrounded_dropped(tmp_path):
    pr, diff, tree, changed = tiny_pr(tmp_path)
    bad = answer("a.py", 3, 3, ev=("utils.py", 88, 90))
    ask = asker({"security": bad, **EMPTY})
    rv = review_pr(pr, diff, tree, changed, [], TEMPLATES, ask, TokenBucket())
    assert rv["findings"] == [] and "ungrounded" in rv["specialists"][AgentType.SECURITY].dropped[0]["reason"]


def test_z5_retrieved_chunk_counts_as_shown(tmp_path):
    from pr_review.retrieval import Hit
    pr, diff, tree, changed = tiny_pr(tmp_path)
    hit = Hit(1, "utils.py", 80, 95, "helper", "\n".join(["pass"] * 16), ("keyword",), 0.1)
    good = answer("a.py", 3, 3, ev=("utils.py", 88, 90))
    ask = asker({"security": good, **EMPTY})
    rv = review_pr(pr, diff, tree, changed, [hit], TEMPLATES, ask, TokenBucket())
    assert len(rv["findings"]) == 1
    text, spans = related_block([hit])
    assert "=== utils.py (lines 80-95) ===" in text and "   88  pass" in text


# Z6/Z7 + end to end: seeded set, fake model, both arms
@needs_heads
@pytest.mark.parametrize("arm", ["search", "nosearch"])
def test_end_to_end_seeded(tmp_path, monkeypatch, arm):
    labels = {p["id"]: p for p in json.loads((ROOT / "golden/labels_seeded.json").read_text())["prs"]}
    calls = []

    def fake(provider, model, prompt):
        calls.append(prompt)
        m = re.search(r"PR title: (.*)", prompt)
        pr = next(p for p in labels.values() if p["title"] == m.group(1))
        if pr["clean"] or "SECURITY reviewer" not in prompt:
            return '{"findings": []}'
        lab = pr["expected"][0]
        return answer(lab["file_path"], lab["line_start"], lab["line_start"])

    monkeypatch.setattr("pr_review.embedder.get", lambda key: HashEmbedder(32))
    db, cache = tmp_path / "ix.db", tmp_path / "cache"

    def run(complete=fake):
        return rung3(ROOT, "fake", "fake-model", None, arm=arm, complete=complete, index_db=db, cache_dir=cache,
                     bucket=TokenBucket(10**6))

    res = run()
    assert len(calls) == 14 * 4 and res["seeded"]["totals"]["false_alarms_on_clean_prs"] == 0
    s01 = next(r for r in res["seeded"]["prs"] if r["id"] == "S01")
    assert s01["found"] and s01["findings"][0]["specialist"] == "security" and not s01["partial"]
    assert s01["found_by"] == {"S01": ["security"]}
    tr = res["trace"][0]
    assert ("retrieval" in tr) == (arm == "search")
    if arm == "search":
        assert res["embedder"] == "hash-32" and tr["retrieval"]["mode"] in ("hybrid", "keyword-only")
        assert sqlite3.connect(db).execute("SELECT COUNT(*) FROM chunks").fetchone()[0] > 0
    calls.clear()
    run()
    assert calls == []                                          # Z6: everything answered from the cache
    for p in cache.glob("*_docs.json"):
        rec = json.loads(p.read_text())
        rec["prompt_sha"] = "different"
        p.write_text(json.dumps(rec))
    run()
    assert len(calls) == 14                                     # Z7: only the docs answers (other sha) re-asked


@needs_heads
def test_z3_quota_then_resume_end_to_end(tmp_path):
    seen, tripped = [], []

    def fake(provider, model, prompt):
        seen.append(prompt)
        if len(seen) == 10 and not tripped:                     # the quota runs out once, on the 10th call
            tripped.append(True)
            raise QuotaExhausted("daily limit")
        return '{"findings": []}'
    kw = dict(arm="nosearch", index_db=tmp_path / "ix.db", cache_dir=tmp_path / "c")
    res = rung3(ROOT, "fake", "m", None, complete=fake, bucket=TokenBucket(10**6), **kw)
    assert res["stopped"].startswith("daily quota exhausted at") and len(res["seeded"]["prs"]) < 14
    answered = len(list((tmp_path / "c").glob("*.json")))
    seen.clear()
    res = rung3(ROOT, "fake", "m", None, complete=fake, bucket=TokenBucket(10**6), **kw)
    assert not res["stopped"] and len(res["seeded"]["prs"]) == 14 and len(seen) == 14 * 4 - answered
