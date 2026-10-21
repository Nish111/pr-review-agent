"""The Finding contract: the unit that flows from specialists to the aggregator to GitHub.

Fields follow pr-review-agent.html section 3.4, plus `evidence`: the code spans the finding cites. Evidence is
what makes invariant `every_posted_finding_is_grounded` checkable: a finding whose location is not inside
code the specialist actually received is ungrounded, and gets dropped
(kickoff Q11: no confident, wrong findings).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pr_review.contracts.errors import ContractError


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentType(str, Enum):
    STATIC = "static"        # rung 1: rule-based checks
    SINGLE = "single"        # rung 2: one LLM reviewer
    SECURITY = "security"    # rung 3: the four specialists
    QUALITY = "quality"
    TESTS = "tests"
    DOCS = "docs"


def _check_path(path: str) -> str:
    if not isinstance(path, str) or not path.strip():
        raise ContractError("file_path must be a non-empty string")
    p = path.replace("\\", "/")
    if p.startswith("/") or ":" in p.split("/")[0] or ".." in p.split("/"):
        raise ContractError(f"file_path must be repo-relative, got {path!r}")
    return p


@dataclass(frozen=True)
class Span:
    """A repo-relative file plus an inclusive 1-based line range."""
    file_path: str
    line_start: int
    line_end: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "file_path", _check_path(self.file_path))
        if not (isinstance(self.line_start, int) and isinstance(self.line_end, int)):
            raise ContractError("line numbers must be integers")
        if self.line_start < 1 or self.line_end < self.line_start:
            raise ContractError(f"bad line range {self.line_start}-{self.line_end}")

    def within(self, other: Span) -> bool:
        return (self.file_path == other.file_path
                and other.line_start <= self.line_start and self.line_end <= other.line_end)


@dataclass(frozen=True)
class Finding:
    agent_type: AgentType
    severity: Severity
    category: str
    summary: str
    location: Span
    confidence: float
    rationale: str
    suggestion: str = ""
    evidence: tuple[Span, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name in ("category", "summary", "rationale"):
            v = getattr(self, name)
            if not isinstance(v, str) or not v.strip():
                raise ContractError(f"{name} must be a non-empty string")
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise ContractError("confidence must be a number")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ContractError(f"confidence must be in [0, 1], got {self.confidence}")

    def is_grounded(self, context: list[Span] | tuple[Span, ...]) -> bool:
        """True only if the finding's location AND every cited evidence span lie inside code the
        specialist actually received. No evidence at all counts as ungrounded."""
        if not self.evidence:
            return False
        spans = (self.location, *self.evidence)
        return all(any(s.within(c) for c in context) for s in spans)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Finding:
        """Parse untrusted (e.g. LLM) output. Anything malformed raises ContractError: nothing is guessed."""
        if not isinstance(d, dict):
            raise ContractError("finding must be an object")
        try:
            loc = Span(d["file_path"], d["line_start"], d["line_end"])
            evidence = tuple(Span(e["file_path"], e["line_start"], e["line_end"])
                             for e in d.get("evidence", []))
            return cls(
                agent_type=AgentType(d["agent_type"]),
                severity=Severity(d["severity"]),
                category=d["category"],
                summary=d["summary"],
                location=loc,
                confidence=d["confidence"],
                rationale=d["rationale"],
                suggestion=d.get("suggestion", ""),
                evidence=evidence,
            )
        except KeyError as e:
            raise ContractError(f"missing field {e.args[0]!r}") from None
        except (TypeError, ValueError) as e:
            if isinstance(e, ContractError):
                raise
            raise ContractError(str(e)) from None
