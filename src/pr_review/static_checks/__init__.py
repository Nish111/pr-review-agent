"""Rung 1: rule-based checks (eval/PREREG_RUNG1.md). Deterministic: same tree -> same findings."""

from pr_review.static_checks.ruff_check import RULES, review_tree

__all__ = ["RULES", "review_tree"]
