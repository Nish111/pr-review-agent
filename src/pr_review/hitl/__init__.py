"""The approval queue (matrix 05: G8, G9, G11). Nothing here posts to GitHub; posting goes through the M4 outbox."""

from pr_review.hitl.queue import ApprovalQueue

__all__ = ["ApprovalQueue"]
