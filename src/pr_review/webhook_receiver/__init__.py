"""Ingress: GitHub webhook -> at most one review job per PR commit (FAILURE_MATRIX_01_INGRESS.md)."""

from pr_review.webhook_receiver.receiver import Receiver, Reply

__all__ = ["Receiver", "Reply"]
