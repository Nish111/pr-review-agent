"""Fixtures for the ingress tests. The payload builders live in pr_review.webhook_receiver.payloads."""

import pytest

from pr_review.store import connect
from pr_review.webhook_receiver import Receiver
from pr_review.webhook_receiver.payloads import SECRET, comment_event, pr_event, signed

__all__ = ["SECRET", "comment_event", "pr_event", "signed"]


class Clock:
    def __init__(self, t=1_761_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def rx(tmp_path, clock):
    conn = connect(str(tmp_path / "store.db"))
    return Receiver(conn, (SECRET,), tmp_path / "inbox.jsonl", head_sha_of=lambda repo, pr: "b" * 40,
                    clock=clock)


def jobs(rx, state=None):
    q = "SELECT * FROM jobs" + (" WHERE state=?" if state else "") + " ORDER BY id"
    return rx.conn.execute(q, (state,) if state else ()).fetchall()
