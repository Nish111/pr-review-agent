"""Calibration (G4) and threshold choice (G5). A group's score = smoothed right-rate of training groups with the same
features: (right + M * p0) / (n + M), p0 = the overall right-rate in training. Threshold = the lowest score at which the
posted training groups reach the target precision; None if no score does (then everything goes to the queue)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

M = 2.0                    # add-M smoothing toward the overall rate: 1-2 examples can't make a 100% score
TARGET = 0.90              # G0
MIN_POSTED = 3             # a threshold must post at least this many training groups to count


@dataclass
class Calibration:
    table: dict[tuple, tuple[int, int]]       # features -> (right, total)
    p0: float

    @classmethod
    def fit(cls, rows: list[tuple[tuple, bool]]) -> Calibration:
        table: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
        for feat, right in rows:
            table[feat][0] += int(right)
            table[feat][1] += 1
        p0 = sum(int(r) for _, r in rows) / len(rows) if rows else 0.0
        return cls({k: (v[0], v[1]) for k, v in table.items()}, p0)

    def score(self, feat: tuple) -> float:
        right, n = self.table.get(feat, (0, 0))
        return round((right + M * self.p0) / (n + M), 4)


def choose_threshold(scored: list[tuple[float, bool]], target: float = TARGET) -> float | None:
    """Lowest threshold whose posted set (score >= t) has precision >= target and at least MIN_POSTED items."""
    for t in sorted({s for s, _ in scored}):
        posted = [r for s, r in scored if s >= t]
        if len(posted) >= MIN_POSTED and sum(posted) / len(posted) >= target:
            return t
    return None


def leave_one_pr_out(rows: list[tuple[str, tuple, bool]], target: float = TARGET) -> dict:
    """rows: (pr, features, right). For each PR: fit + choose on the others, apply to it. Returns the pooled result."""
    prs = sorted({pr for pr, _, _ in rows})
    posted = right_posted = 0
    folds = []
    for held in prs:
        train = [(f, r) for p, f, r in rows if p != held]
        cal = Calibration.fit(train)
        t = choose_threshold([(cal.score(f), r) for f, r in train], target)
        test = [(cal.score(f), r) for p, f, r in rows if p == held]
        post = [r for s, r in test if t is not None and s >= t]
        posted += len(post)
        right_posted += sum(post)
        folds.append({"pr": held, "threshold": t, "posted": len(post), "right_posted": sum(post), "groups": len(test)})
    return {"posted": posted, "right_posted": right_posted,
            "precision": round(right_posted / posted, 3) if posted else None, "folds": folds,
            "folds_without_threshold": sum(1 for f in folds if f["threshold"] is None)}
