"""Rung 2 plumbing with a fake model: no network, no quota. The real run happens via `eval --rung 2`."""

import json
import shutil
from pathlib import Path

import pytest

from pr_review.contracts import Span
from pr_review.evaluation.run_llm import rung2
from pr_review.llm_client import QuotaExhausted
from pr_review.specialists.single import MAX_PROMPT_TOKENS, build_prompt, estimate_tokens, parse_response

ROOT = Path(__file__).resolve().parents[1]
CTX = [Span("a.py", 1, 50)]


def _item(**over):
    d = {"severity": "high", "category": "sql-injection", "summary": "s", "file_path": "a.py",
         "line_start": 10, "line_end": 10, "confidence": 0.9, "rationale": "r",
         "evidence": [{"file_path": "a.py", "line_start": 9, "line_end": 11}]}
    d.update(over)
    return d


def test_parse_keeps_grounded_and_drops_the_rest():
    raw = "```json\n" + json.dumps({"findings": [
        _item(),
        _item(file_path="other.py", evidence=[{"file_path": "other.py", "line_start": 1, "line_end": 1}]),
        _item(confidence=7), _item(evidence=[])]}) + "\n```"
    p = parse_response(raw, CTX)
    assert len(p.findings) == 1 and p.findings[0].agent_type.value == "single"
    assert [d["reason"].split(":")[0] for d in p.dropped] == ["ungrounded", "contract", "ungrounded"]


def test_unparseable_answer_is_an_error_not_an_empty_review():
    p = parse_response("Looks good to me!", CTX)
    assert p.parse_error and not p.findings


def test_prompt_respects_budget_and_numbers_lines(tmp_path):
    (tmp_path / "a.py").write_text("\n".join(f"x{i} = {i}" for i in range(1, 3000)))
    pr = {"id": "X", "title": "t", "body": "b"}
    tmpl = "T {title} {body} {diff} {files}"
    prompt, spans, mode = build_prompt(tmpl, pr, "+x", tmp_path, {"a.py": {1500}})
    assert estimate_tokens(prompt) <= MAX_PROMPT_TOKENS and mode != "whole-files"
    assert " 1500  x1500 = 1500" in prompt and spans == [Span("a.py", 1470, 1530)]


@pytest.fixture
def repo(tmp_path):
    """A throwaway copy of the bits rung2() reads, so the real eval/results is never touched."""
    for rel in ("prompts", "golden/labels_seeded.json", "golden/labels_real.json", "golden/seeded/prs"):
        src, dst = ROOT / rel, tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if src.is_dir() else shutil.copy)(src, dst)
    head = ROOT / "golden/seeded/head"
    if not head.is_dir():
        pytest.skip("run golden/seeded/build.py first")
    shutil.copytree(head, tmp_path / "golden/seeded/head")
    return tmp_path


def test_fake_model_end_to_end_and_cache(repo):
    calls = []

    def fake(provider, model, prompt):
        calls.append(1)
        return json.dumps({"findings": []})

    r1 = rung2(repo, "fake", "m1", None, complete=fake)
    assert len(calls) == 14 and r1["seeded"]["totals"]["findings"] == 0
    rung2(repo, "fake", "m1", None, complete=fake)
    assert len(calls) == 14                       # all 14 answers reused from the cache
    rung2(repo, "fake", "m2", None, complete=fake)
    assert len(calls) == 28                       # different model -> asked again


def test_failed_call_is_not_cached_as_success_and_quota_stops_run(repo):
    def broken(provider, model, prompt):
        raise RuntimeError("connection reset")

    r = rung2(repo, "fake", "m", None, complete=broken)
    assert all(not t["call_ok"] for t in r["trace"])
    seen = []

    def quota(provider, model, prompt):
        seen.append(1)
        raise QuotaExhausted("daily")

    r = rung2(repo, "fake", "m", None, complete=quota)
    assert len(seen) == 1 and r["stopped"].startswith("daily quota exhausted")


def test_right_reason_handcheck_roundtrip(repo):
    from pr_review.evaluation import right_reason as rr

    (repo / "eval/results").mkdir(parents=True, exist_ok=True)
    res = {"seeded": {"prs": [{"id": "S01", "findings": [
        {"file": "notes_svc/notes.py", "lines": [32, 33], "message": "SQL injection via f-string",
         "rationale": "keyword pasted", "matched": True},
        {"file": "notes_svc/notes.py", "lines": [1, 1], "message": "x", "matched": False}]}]},
        "real": {"prs": []}}
    (repo / "eval/results/rung2.json").write_text(json.dumps(res))
    items = rr.matched_items(repo, 2)
    assert [i["id"] for i in items] == ["M1"] and "SQL" in items[0]["label"].upper()
    p = rr.write_handcheck(repo, 2)
    p.write_text(p.read_text().replace("**Your answer:** ", "**Your answer:** Yes, same bug"))
    assert rr.read_handcheck(repo, 2) == {"M1": True}
    out = rr.run_judge(repo, 2, "fake", "j", complete=lambda *a: '{"same_bug": false, "reason": "no"}')
    assert out["verdicts"] == [{"id": "M1", "same_bug": False, "reason": "no"}]
