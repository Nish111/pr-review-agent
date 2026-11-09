"""Regression gate (matrix 07, L6) and recalibration report (L7). Deterministic; no model calls."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from pr_review.aggregator import Calibration, choose_threshold, features, group_findings, leave_one_pr_out
from pr_review.evaluation.run_rung4 import _key, truth

MAX_PRECISION_DROP = 0.05


def gate(root: Path, baseline: dict, candidate: dict, labels_rung: str = "3n") -> dict:
    b, c = baseline["seeded"]["totals"], candidate["seeded"]["totals"]
    reasons = []
    if (c["recall"] or 0) < (b["recall"] or 0):
        reasons.append(f"location recall dropped {b['recall']} -> {c['recall']}")
    if (c["precision"] or 0) < (b["precision"] or 0) - MAX_PRECISION_DROP:
        reasons.append(f"location precision dropped {b['precision']} -> {c['precision']} "
                       f"(more than {MAX_PRECISION_DROP})")
    if c["false_alarms_on_clean_prs"] > b["false_alarms_on_clean_prs"]:
        fb, fc = b["false_alarms_on_clean_prs"], c["false_alarms_on_clean_prs"]
        reasons.append(f"false alarms on clean PRs rose {fb} -> {fc}")
    known = truth(root, labels_rung)
    unlabelled = [f"{r['id']} {f['file']}:{f['lines'][0]} {f['message'][:60]}"
                  for r in candidate["seeded"]["prs"] for f in r["findings"]
                  if f.get("matched") and _key(r["id"], f["file"], f["lines"], f["message"]) not in known]
    verdict = "fail" if reasons else "needs hand check" if unlabelled else "pass"
    return {"verdict": verdict, "reasons": reasons, "unlabelled_matched": unlabelled,
            "baseline": {k: b[k] for k in ("precision", "recall", "false_alarms_on_clean_prs")},
            "candidate": {k: c[k] for k in ("precision", "recall", "false_alarms_on_clean_prs")}}


def recalibrate(root: Path, store: Path | None, rung: str = "3n") -> dict:
    """Golden labels + queue verdicts -> a new calibration table and leave-one-out result. Reports; never applies."""
    res = json.loads((root / f"eval/results/rung{rung}.json").read_text(encoding="utf-8"))
    t = truth(root, rung)
    rows = []
    for row in res["seeded"]["prs"]:
        for g in group_findings(row["id"], row["findings"]):
            right = t.get(_key(row["id"], g.lead["file"], g.lead["lines"], g.lead["message"]))
            if right is not None:
                rows.append((row["id"], features(g), right))
    sources = {"golden": len(rows)}
    if store is not None and store.is_file():
        conn = sqlite3.connect(store)
        q = conn.execute("SELECT a.work_key, a.features, l.right, l.source FROM approvals a JOIN calibration_labels l "
                         "ON l.fingerprint = a.fingerprint WHERE a.features IS NOT NULL").fetchall()
        for work_key, feat, right, source in q:
            rows.append((work_key, tuple(feat.split(" / ")), bool(right)))
            sources[f"queue:{source}"] = sources.get(f"queue:{source}", 0) + 1
    cal = Calibration.fit([(f, r) for _, f, r in rows])
    return {"sources": sources, "leave_one_out": leave_one_pr_out(rows),
            "threshold_if_applied": choose_threshold([(cal.score(f), r) for _, f, r in rows]),
            "table": {" / ".join(k): {"right": v[0], "total": v[1], "score": cal.score(k)}
                      for k, v in sorted(cal.table.items())},
            "applied": False, "note": "report only: changing the live threshold is a human decision (like S6)"}
