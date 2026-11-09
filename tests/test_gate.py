"""Matrix 07 tests Q1-Q4."""

import copy
import json
import sqlite3
from pathlib import Path

import pytest

from pr_review.evaluation.gate import gate, recalibrate
from pr_review.hitl import ApprovalQueue

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "eval/results/rung3n.json"
needs = pytest.mark.skipif(not BASE.is_file(), reason="needs the committed rung 3 results")


@needs
def test_q1_q2_q3_gate():
    base = json.loads(BASE.read_text(encoding="utf-8"))
    assert gate(ROOT, base, copy.deepcopy(base))["verdict"] == "pass"                       # Q2
    worse = copy.deepcopy(base)
    worse["seeded"]["totals"]["recall"] = 0.5
    r = gate(ROOT, base, worse)
    assert r["verdict"] == "fail" and "recall dropped" in r["reasons"][0]                   # Q1
    new = copy.deepcopy(base)
    row = next(r for r in new["seeded"]["prs"] if r["findings"])
    row["findings"].append({**row["findings"][0], "message": "a brand-new wording never labelled", "matched": True})
    assert gate(ROOT, base, new)["verdict"] == "needs hand check"                           # Q3


@needs
def test_q4_recalibration_reports_queue_labels_and_applies_nothing(tmp_path):
    from pr_review import config
    before = config.threshold()
    db = tmp_path / "store.db"
    q = ApprovalQueue(sqlite3.connect(db, isolation_level=None))
    q.enqueue("acme/x#1@a", "a.py", 1, 2, "x", 0.5, "docs / restated / alone / high")
    q.reject(1, "nishant")
    pid = q.record_posted("acme/x#1@a", "b.py", 5, 6, "y", 0.93, "security / bug / agree / high")
    q.dispute(pid, "dev", "false positive")
    r = recalibrate(ROOT, db)
    assert r["sources"]["queue:rejected"] == 1 and r["sources"]["queue:disputed"] == 1 and not r["applied"]
    assert config.threshold() == before                                                     # nothing applied
