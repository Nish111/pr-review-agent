"""One SQLite file for jobs, deliveries, findings and events (decision S3)."""

from pr_review.store.db import connect

__all__ = ["connect"]
