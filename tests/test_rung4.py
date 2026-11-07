"""Matrix 05 tests K1-K8 (K4 is M1's route tests, already in test_contracts.py)."""

import sqlite3
from pathlib import Path

import pytest

from pr_review.aggregator import Calibration, choose_threshold, features, group_findings, is_restated, leave_one_pr_out
from pr_review.hitl import ApprovalQueue

ROOT = Path(__file__).resolve().parents[1]


def f(spec, lines, rule, msg, conf=0.9, file="notes_svc/notes.py"):
    return {"file": file, "lines": list(lines), "rule": rule, "message": msg, "specialist": spec, "confidence": conf}


# K1: the S01 shape: security + tests + docs on the same lines -> one comment, bug comment as lead
def test_k1_group_and_fold():
    gs = group_findings("S01", [f("docs", (29, 34), "missing-doc", "Docstring doesn't warn about injection", 0.95),
                                f("security", (31, 34), "sql-injection", "keyword interpolated into SQL", 0.9),
                                f("tests", (31, 34), "missing-test", "injection not covered by any test", 0.99),
                                f("quality", (60, 61), "logic-bug", "other place", 0.7)])
    assert len(gs) == 2
    g = gs[0]
    assert g.lead["specialist"] == "security" and len(g.supporting) == 2
    assert features(g) == ("security", "bug", "agree", "high")
    assert is_restated(g.supporting[0]) and is_restated(g.supporting[1])


def test_group_of_only_test_doc_comments_leads_with_one_of_them():
    g = group_findings("C01", [f("docs", (1, 2), "missing-doc", "README omits get_tags", 0.8)])[0]
    assert features(g) == ("docs", "restated", "alone", "high")


# K2/K3: calibration, threshold, honest "no threshold"
def test_k2_smoothing_and_threshold():
    rows = [(("security", "bug", "agree", "high"), True)] * 6 + [(("docs", "restated", "alone", "high"), False)] * 6
    cal = Calibration.fit(rows)
    hi, lo = cal.score(rows[0][0]), cal.score(rows[-1][0])
    assert 0.5 < hi < 1.0 and 0.0 < lo < 0.5                     # smoothed: never exactly 1 or 0
    assert choose_threshold([(cal.score(ft), r) for ft, r in rows]) == hi


def test_k3_no_threshold_when_target_unreachable():
    rows = [(("docs", "restated", "alone", "high"), i % 2 == 0) for i in range(10)]
    cal = Calibration.fit(rows)
    assert choose_threshold([(cal.score(ft), r) for ft, r in rows]) is None


def test_k2_leave_one_pr_out_never_sees_the_held_pr():
    good, bad = ("security", "bug", "agree", "high"), ("docs", "restated", "alone", "high")
    rows = [(f"P{i:02}", good, True) for i in range(20)] + [(f"P{i:02}", bad, False) for i in range(20)]
    rows.append(("P09", good, False))                             # the only failure of 'good' is in P09
    res = leave_one_pr_out(rows)
    p9 = next(x for x in res["folds"] if x["pr"] == "P09")
    assert p9["threshold"] is not None and p9["posted"] == 2 and p9["right_posted"] == 1
    assert res["posted"] == 21 and res["right_posted"] == 20 and res["folds_without_threshold"] == 0


# K5, K6, K8: the queue
def test_k5_k6_k8_queue():
    clock = [1000.0]
    q = ApprovalQueue(sqlite3.connect(":memory:", isolation_level=None), clock=lambda: clock[0])
    assert q.enqueue("acme/x#1@a", "a.py", 3, 4, "SQL injection", 0.6, "bug")
    assert not q.enqueue("acme/x#1@a", "a.py", 3, 4, "SQL injection", 0.6, "bug")      # K8: re-run adds nothing
    q.enqueue("acme/x#1@a", "b.py", 9, 9, "docs", 0.3, "doc")
    clock[0] += 3 * 86400
    pend = q.pending()
    assert [p["where"] for p in pend] == ["a.py:3-4", "b.py:9-9"] and all(p["stale"] for p in pend)   # K5
    q.approve(pend[0]["id"], "nishant")
    q.reject(pend[1]["id"], "nishant", "not a real problem")
    q.dispute(pend[0]["id"], "dev", "this query is parameterised upstream")                # K6
    labels = dict(q.conn.execute("SELECT source, right FROM calibration_labels").fetchall())
    assert labels == {"disputed": 0, "rejected": 0}
    with pytest.raises(ValueError):
        q.approve(pend[1]["id"], "nishant")                      # a rejected item can't be approved later


# K7: the bot never approves or merges a PR
def test_k7_no_approve_or_merge_calls():
    src = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "src").rglob("*.py"))
    for banned in ('"APPROVE"', "'APPROVE'", "/merge", "REQUEST_CHANGES"):
        assert banned not in src, banned


def test_default_configuration_matches_decision_s6():
    from pr_review import config
    assert config.SEARCH is False
    th = config.threshold()
    assert th is None or 0.8 < th < 0.9                           # 0.84 when rung4n.json is present


def test_missing_calibration_means_everything_to_the_queue(monkeypatch, tmp_path):
    from pr_review import config
    monkeypatch.setattr(config, "CALIBRATION", tmp_path / "missing.json")
    assert config.threshold() is None
