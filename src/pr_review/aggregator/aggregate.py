"""Grouping (G1) and restatement folding (G2). Works on finding rows as saved in rung3.json:
{"file", "lines": [a, b], "rule" (category), "message", "specialist", "confidence", "severity"}."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

TOL = 3                       # same tolerance as scoring (evaluation/score.py)
_RESTATED = re.compile(r"missing[-_ ]?(test|tests|doc|docs|documentation|coverage|assertion)|test[-_ ]?coverage|"
                       r"untested|undocumented|not (covered|exercised|tested|documented)|no test|docstring|"
                       r"documentation|readme|changelog|help text", re.IGNORECASE)


def is_restated(f: dict) -> bool:
    """A 'missing test / missing doc' kind of comment (G2), judged from its category and summary."""
    return bool(_RESTATED.search(f.get("rule", "")) or _RESTATED.search(f.get("message", "")))


@dataclass
class Group:
    pr: str
    members: list[dict] = field(default_factory=list)

    @property
    def lead(self) -> dict:
        """The comment that gets posted: the most confident bug comment; a test/doc one only if there is no other."""
        bugs = [f for f in self.members if not is_restated(f)]
        pool = bugs or self.members
        return max(pool, key=lambda f: (f.get("confidence", 0.0), -f["lines"][0], f["message"]))

    @property
    def supporting(self) -> list[dict]:
        return [f for f in self.members if f is not self.lead]

    @property
    def specialists(self) -> set[str]:
        return {f.get("specialist", "") for f in self.members}


def group_findings(pr: str, findings: list[dict]) -> list[Group]:
    """G1: same file and line ranges within TOL of each other -> one group, whatever the category (union-find)."""
    parent = list(range(len(findings)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, a in enumerate(findings):
        for j in range(i):
            b = findings[j]
            if a["file"] == b["file"] and a["lines"][0] <= b["lines"][1] + TOL and b["lines"][0] <= a["lines"][1] + TOL:
                parent[root(i)] = root(j)
    groups: dict[int, Group] = {}
    for i, f in enumerate(findings):
        groups.setdefault(root(i), Group(pr)).members.append(f)
    return sorted(groups.values(), key=lambda g: (g.lead["file"], g.lead["lines"][0]))


def features(g: Group) -> tuple[str, str, str, str]:
    """The pre-registered score features (PREREG_RUNG4): specialist, kind, agreement, confidence band."""
    lead = g.lead
    return (lead.get("specialist", ""), "restated" if is_restated(lead) else "bug",
            "agree" if len(g.specialists) >= 2 else "alone", "high" if lead.get("confidence", 0.0) >= 0.8 else "low")
