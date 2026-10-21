"""One review job, and the work key that makes duplicates detectable (ingress matrix F8/F9;
invariant `one_live_job_per_work_key`)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from pr_review.contracts.errors import ContractError

_SHA = re.compile(r"^[0-9a-f]{7,40}$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class Trigger(str, Enum):
    PULL_REQUEST = "pull_request"      # opened / synchronize / reopened / ready_for_review
    REVIEW_COMMAND = "review_command"  # a member commented /review (ingress F7, F10, F17)


@dataclass(frozen=True)
class WorkKey:
    repo: str
    pr_number: int
    head_sha: str

    def __post_init__(self) -> None:
        if not _REPO.match(self.repo or ""):
            raise ContractError(f"repo must look like owner/name, got {self.repo!r}")
        if isinstance(self.pr_number, bool) or not isinstance(self.pr_number, int) or self.pr_number < 1:
            raise ContractError("pr_number must be a positive integer")
        sha = (self.head_sha or "").lower()
        if not _SHA.match(sha):
            raise ContractError(f"head_sha must be 7-40 hex characters, got {self.head_sha!r}")
        object.__setattr__(self, "head_sha", sha)

    def __str__(self) -> str:
        return f"{self.repo}#{self.pr_number}@{self.head_sha}"


@dataclass(frozen=True)
class Job:
    work_key: WorkKey
    delivery_id: str
    trigger: Trigger
    received_at: str          # ISO-8601 UTC, set by ingress
    is_fork: bool = False     # ingress F5: fork jobs get a reduced tool scope

    def __post_init__(self) -> None:
        if not isinstance(self.delivery_id, str) or not self.delivery_id.strip():
            raise ContractError("delivery_id must be a non-empty string")
