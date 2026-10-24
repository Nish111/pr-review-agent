import json
from pathlib import Path

from pr_review.evaluation.golden import changed_lines, check

ROOT = Path(__file__).resolve().parents[1]

DIFF = """--- a/x.py
+++ b/x.py
@@ -1,3 +1,4 @@
 a
-b
+B
+c
 d
--- /dev/null
+++ b/new.py
@@ -0,0 +1,2 @@
+one
+two
"""


def test_changed_lines_counts_head_side_only():
    assert changed_lines(DIFF) == {"x.py": {2, 3}, "new.py": {1, 2}}


def test_committed_seeded_set_passes_the_check():
    r = check(ROOT / "golden/labels_seeded.json", ROOT)
    assert r.ok, r.problems
    assert (r.total, r.planted, r.clean) == (14, 10, 4)


def test_label_on_untouched_line_is_caught(tmp_path):
    (tmp_path / "p.diff").write_text(DIFF)
    labels = {"prs": [{"id": "X", "diff": "p.diff", "clean": False,
                       "expected": [{"file_path": "x.py", "line_start": 4, "line_end": 4}]}]}
    (tmp_path / "l.json").write_text(json.dumps(labels))
    r = check(tmp_path / "l.json", tmp_path)
    assert not r.ok and "not on a line the PR changed" in r.problems[0]


def test_clean_flag_must_agree_with_labels(tmp_path):
    (tmp_path / "p.diff").write_text(DIFF)
    labels = {"prs": [{"id": "X", "diff": "p.diff", "clean": True,
                       "expected": [{"file_path": "x.py", "line_start": 2, "line_end": 2}]}]}
    (tmp_path / "l.json").write_text(json.dumps(labels))
    assert not check(tmp_path / "l.json", tmp_path).ok


def test_committed_real_set_passes_the_check():
    r = check(ROOT / "golden/labels_real.json", ROOT)
    assert r.ok, r.problems
    assert (r.total, r.real, r.clean, r.known_problems) == (5, 5, 0, 6)
