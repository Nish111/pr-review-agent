"""Matrix 06 tests V1-V6."""

import json
import re
from pathlib import Path

import pytest

from pr_review.contracts import AgentType
from pr_review.orchestrator import TokenBucket, review_pr

ROOT = Path(__file__).resolve().parents[1]
HAVE_RUNS = (ROOT / "eval/results/rung3n.json").is_file() and (ROOT / "golden/seeded/head/S01").is_dir()
needs_runs = pytest.mark.skipif(not HAVE_RUNS, reason="needs the committed rung 3 results and golden/seeded/head")


def test_v1_measured_usage_is_saved(tmp_path, monkeypatch):
    import pr_review.evaluation.run_llm as rl
    import pr_review.llm_client as lc

    def fake(provider, model, prompt):
        return '{"findings": []}'
    monkeypatch.setattr(rl, "real_complete", fake)
    monkeypatch.setattr(lc, "last_usage", lambda: {"input_tokens": 1200, "output_tokens": 300, "reasoning_tokens": 250})
    rec = rl._ask(tmp_path / "x.json", {"k": 1}, "p", "groq", "m", fake)
    assert rec["usage"] == {"input_tokens": 1200, "output_tokens": 300, "reasoning_tokens": 250, "measured": True}


def test_v2_budget_guard_skips_lowest_priority(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    diff = "--- a/a.py\n+++ b/a.py\n@@ -1,1 +1,1 @@\n-x = 0\n+x = 1\n"
    big = "X" * 18_000 + "{title}{body}{diff}{files}{context}"      # ~4,500 tokens + 1,500 answer reserve = ~6,000
    tmpl = {a: big for a in AgentType if a.value in ("security", "quality", "tests", "docs")}
    asked = []

    def ask(agent, prompt):
        asked.append(agent.value)
        return {"ok": True, "raw": '{"findings": []}'}
    rv = review_pr({"id": "P"}, diff, tmp_path, {"a.py": {1}}, [], tmpl, ask, TokenBucket(10**6), budget=13_000)
    assert sorted(asked) == ["quality", "security"] and rv["partial"]         # priority order: security, quality first
    assert "BudgetGuard" in rv["specialists"][AgentType.DOCS].error


@needs_runs
def test_v3_v4_trace_states_and_prompt_check():
    from pr_review.trace import build_trace, render
    t = build_trace(ROOT, "S01")
    specs = [s for s in t["steps"] if s["step"].startswith("specialist:")]
    assert len(specs) == 4 and all(s["prompt_check"] == "matches what the model saw" for s in specs)   # V4
    r2 = build_trace(ROOT, "R2")
    assert {s["state"] for s in r2["steps"] if s["step"].startswith("specialist:")} == {"not sent"}       # V3
    assert "not sent" in render(r2)


@needs_runs
def test_v5_v6_report_has_no_secrets_and_cost_recomputes():
    from pr_review.reports import build_report
    from pr_review.reports.build import PRICE, economics
    page = build_report(ROOT).read_text(encoding="utf-8")
    assert not re.search(r"gsk_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN", page)
    e = economics(ROOT, "2")
    tr = json.loads((ROOT / "eval/results/rung2.json").read_text(encoding="utf-8"))["trace"]
    tin = sum(t["est_tokens"] for t in tr if t.get("sent"))
    raw = [json.loads((ROOT / f"eval/results/rung2_raw/{t['pr']}.json").read_text(encoding="utf-8"))["raw"]
           for t in tr if t.get("sent")]
    tout = sum(len(r) // 4 for r in raw)
    assert e["tokens_in_est"] == tin
    assert e["usd_if_paid_lower_bound"] == round(tin / 1e6 * PRICE["input"] + tout / 1e6 * PRICE["output"], 4)
