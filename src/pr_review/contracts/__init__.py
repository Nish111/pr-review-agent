"""The data shapes every other module agrees on. This package imports nothing from the project
(context-graph.json invariant `dependencies_point_inward`)."""

from pr_review.contracts.errors import ContractError
from pr_review.contracts.finding import AgentType, Finding, Severity, Span
from pr_review.contracts.job import Job, Trigger, WorkKey
from pr_review.contracts.review import Review, Route, route

__all__ = [
    "AgentType", "ContractError", "Finding", "Job", "Review", "Route", "Severity", "Span",
    "Trigger", "WorkKey", "route",
]
