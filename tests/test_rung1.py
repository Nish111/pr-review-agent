"""Rung 1 and the scorer, on tiny synthetic inputs (the golden set itself is only scored via `eval`)."""

from pathlib import Path

from pr_review.contracts import AgentType, Finding, Severity, Span
from pr_review.evaluation.score import matches, score_pr, totals
from pr_review.static_checks import review_tree


def _f(path, a, b=None):
    s = Span(path, a, b or a)
    return Finding(AgentType.STATIC, Severity.HIGH, "X1", "m", s, 1.0, "r", evidence=(s,))


LABEL = {"file_path": "a.py", "line_start": 10, "line_end": 12}


def test_match_needs_same_file_and_overlap_within_3_lines():
    assert matches(_f("a.py", 7), LABEL) and matches(_f("a.py", 15), LABEL)
    assert not matches(_f("a.py", 6), LABEL) and not matches(_f("a.py", 16), LABEL)
    assert not matches(_f("b.py", 11), LABEL)


def test_problem_counted_once_even_if_several_ranges_hit():
    pr = {"id": "R9", "expected": [dict(LABEL, problem="R9/p"), {"file_path": "a.py", "line_start": 40,
                                                                  "line_end": 40, "problem": "R9/p"}]}
    s = score_pr(pr, [_f("a.py", 11), _f("a.py", 40), _f("z.py", 1)])
    assert s.found == {"R9/p"} and s.true_positives == 2 and s.findings == 3


def test_totals_count_false_alarms_on_clean_prs():
    clean = score_pr({"id": "C9", "clean": True, "expected": []}, [_f("a.py", 1)])
    planted = score_pr({"id": "S9", "expected": [LABEL]}, [_f("a.py", 11)])
    t = totals([clean, planted])
    assert t["precision"] == 0.5 and t["recall"] == 1.0 and t["false_alarms_on_clean_prs"] == 1


def test_precision_undefined_when_no_findings():
    assert totals([score_pr({"id": "C9", "clean": True, "expected": []}, [])])["precision"] is None


def test_review_tree_reports_only_changed_lines(tmp_path: Path):
    (tmp_path / "m.py").write_text(
        "from datetime import date\n\n\ndef a():\n    return date.today()\n\n\n"
        "def b():\n    return date.today()\n")
    fs = review_tree(tmp_path, {"m.py": {9}})
    assert [(f.location.line_start, f.category) for f in fs] == [(9, "DTZ011")]
    assert fs[0].agent_type is AgentType.STATIC and fs[0].is_grounded([Span("m.py", 1, 9)])
