"""Rung 4: aggregator + calibrated threshold on rung 3's saved findings (eval/PREREG_RUNG4.md). No model calls.

Truth: matched findings -> the hand check (final round); unmatched findings -> eval/UNMATCHED_RUNG<rung>.md
(Claude's verdicts, sample-checked by Nishant, D2 = A). Reports A (leave one PR out, official), B (in-sample,
optimistic) and C (seeded calibration applied to the real click PRs, per PR)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pr_review.aggregator import Calibration, choose_threshold, features, group_findings, leave_one_pr_out
from pr_review.evaluation.right_reason import matched_items, read_final

_UM = re.compile(r"^## (U\d+) · PR (\S+) · `([^`]+):(\d+)-(\d+)`.*?\*\*Summary:\*\* (.*?)\n"
                 r".*?\*\*Verdict:\*\*[ \t]*([^\n]*)", re.MULTILINE | re.DOTALL)


def _key(pr: str, file: str, lines, message: str) -> tuple:
    return (pr, file, int(lines[0]), int(lines[1]), message.strip())


def truth(root: Path, rung: str) -> dict[tuple, bool | None]:
    out: dict[tuple, bool | None] = {}
    hand = read_final(root, rung)
    for it in matched_items(root, rung):
        out[_key(it["pr"], it["file"], it["lines"], it["summary"])] = hand.get(it["id"])
    path = root / f"eval/UNMATCHED_RUNG{rung}.md"
    if path.is_file():
        for m in _UM.finditer(path.read_text(encoding="utf-8")):
            v = m.group(7).strip().lower()
            out[_key(m.group(2), m.group(3), (m.group(4), m.group(5)), m.group(6))] = (
                True if v.startswith("real") else False if v.startswith("not") else None)
    return out


def rung4(root: Path, rung: str) -> dict:
    res = json.loads((root / f"eval/results/rung{rung}.json").read_text(encoding="utf-8"))
    t = truth(root, rung)
    rows: dict[str, list] = {"seeded": [], "real": []}
    per_pr, missing = [], []
    for part in ("seeded", "real"):
        for row in res[part]["prs"]:
            groups = group_findings(row["id"], row["findings"])
            for g in groups:
                lead = g.lead
                right = t.get(_key(row["id"], lead["file"], lead["lines"], lead["message"]))
                if right is None:
                    missing.append(f"{row['id']} {lead['file']}:{lead['lines'][0]} {lead['message'][:60]}")
                    continue
                rows[part].append((row["id"], features(g), right))
            per_pr.append({"pr": row["id"], "part": part, "comments_before": len(row["findings"]),
                           "comments_after": len(groups)})
    if missing:
        raise ValueError(f"{len(missing)} posted comment(s) have no right/wrong label yet (finish the hand check and "
                         f"eval/UNMATCHED_RUNG{rung}.md first): " + "; ".join(missing[:5]))
    seeded = rows["seeded"]
    a = leave_one_pr_out(seeded)
    cal = Calibration.fit([(f, r) for _, f, r in seeded])
    t_all = choose_threshold([(cal.score(f), r) for _, f, r in seeded])
    post_b = [r for _, f, r in seeded if t_all is not None and cal.score(f) >= t_all]
    c = [{"pr": p, "score": cal.score(f), "posted": t_all is not None and cal.score(f) >= t_all, "right": r}
         for p, f, r in rows["real"]]
    return {"rung": f"4 (on rung {rung})", "groups_seeded": len(seeded), "comments": per_pr,
            "A_leave_one_pr_out": a,
            "B_in_sample": {"threshold": t_all, "posted": len(post_b), "right_posted": sum(post_b),
                            "precision": round(sum(post_b) / len(post_b), 3) if post_b else None},
            "C_real_per_pr": c,
            "calibration_table": {" / ".join(k): {"right": v[0], "total": v[1], "score": cal.score(k)}
                                  for k, v in sorted(cal.table.items())},
            "threshold_for_demo": t_all}
