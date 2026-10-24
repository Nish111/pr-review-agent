"""Score findings against golden labels (rule: GOLDEN_SET_PLAN.md, pre-registered).

A finding matches a label if: same file, and the finding's lines overlap the label's lines widened by
TOLERANCE on each side. A label 'problem' is found if any of its ranges is matched.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pr_review.contracts import Finding

TOLERANCE = 3


def matches(f: Finding, label: dict) -> bool:
    return (f.location.file_path == label["file_path"]
            and f.location.line_start <= label["line_end"] + TOLERANCE
            and f.location.line_end >= label["line_start"] - TOLERANCE)


@dataclass
class PRScore:
    pr_id: str
    clean: bool
    findings: int
    true_positives: int          # findings that match some label
    problems: set[str]           # problem ids in the labels
    found: set[str] = field(default_factory=set)


def score_pr(pr: dict, findings: list[Finding]) -> PRScore:
    labels = pr.get("expected", [])
    pids = [lab.get("problem", f"{pr['id']}/{i}") for i, lab in enumerate(labels)]
    s = PRScore(pr["id"], pr.get("clean", not labels), len(findings), 0, set(pids))
    for f in findings:
        hit = [pid for pid, lab in zip(pids, labels, strict=True) if matches(f, lab)]
        if hit:
            s.true_positives += 1
            s.found.update(hit)
    return s


def totals(scores: list[PRScore]) -> dict:
    n_find = sum(s.findings for s in scores)
    tp = sum(s.true_positives for s in scores)
    n_prob = sum(len(s.problems) for s in scores)
    n_found = sum(len(s.found) for s in scores)
    return {"findings": n_find, "true_positives": tp, "false_alarms": n_find - tp,
            "false_alarms_on_clean_prs": sum(s.findings for s in scores if s.clean),
            "precision": (tp / n_find) if n_find else None,
            "problems": n_prob, "problems_found": n_found,
            "recall": (n_found / n_prob) if n_prob else None}
