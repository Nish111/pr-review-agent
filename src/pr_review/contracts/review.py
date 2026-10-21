"""A review and the routing rule that decides where it goes.

`route` is deterministic on purpose: the decision to bother a human must be identical every time
for the same input (html Move 3, "most common mistake"). There is deliberately no APPROVE route:
invariant `bot_never_approves_or_merges`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pr_review.contracts.errors import ContractError
from pr_review.contracts.finding import Finding, Severity
from pr_review.contracts.job import WorkKey


class Route(str, Enum):
    POST_COMMENT = "post_comment"        # posted as a COMMENT review, never approve / request-changes
    APPROVAL_QUEUE = "approval_queue"    # a human checks it first
    ESCALATE = "escalate"                # CRITICAL finding: human decides (HITL level 4)


@dataclass(frozen=True)
class Review:
    work_key: WorkKey
    findings: tuple[Finding, ...]
    overall_confidence: float
    partial: bool = False     # e.g. 3 of 4 specialists finished: reported as partial, never as complete

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.overall_confidence) <= 1.0:
            raise ContractError("overall_confidence must be in [0, 1]")


def route(review: Review, threshold: float | None) -> Route:
    """Where a review goes.

    threshold=None means 'not calibrated yet' (G0 field 5): every review goes to the approval queue.
    """
    if any(f.severity is Severity.CRITICAL for f in review.findings):
        return Route.ESCALATE
    if threshold is None or review.partial:
        return Route.APPROVAL_QUEUE
    if not 0.0 <= threshold <= 1.0:
        raise ContractError("threshold must be in [0, 1]")
    return Route.POST_COMMENT if review.overall_confidence >= threshold else Route.APPROVAL_QUEUE
