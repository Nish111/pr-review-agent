"""The lecture's ingress design, kept runnable as the 'before' for the before/after numbers
(pr-review-agent.html section 3.1: verify HMAC, check the delivery id, enqueue, return 200).

Deliberately faithful, including its gaps: the duplicate check and the enqueue are two separate steps,
duplicates are detected by delivery id only, there's no write-ahead inbox and no superseding.
Used only by `python -m pr_review ingress-compare`; never in the real path.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from dataclasses import dataclass

SCHEMA = """CREATE TABLE IF NOT EXISTS baseline_jobs (
    id INTEGER PRIMARY KEY, delivery_id TEXT NOT NULL, repo TEXT, pr_number INTEGER, head_sha TEXT)"""


@dataclass
class BaselineReceiver:
    conn: sqlite3.Connection
    secret: str

    def __post_init__(self) -> None:
        self.conn.execute(SCHEMA)

    def handle(self, headers: dict[str, str], body: bytes) -> int:
        h = {k.lower(): v for k, v in headers.items()}
        want = "sha256=" + hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(want, h.get("x-hub-signature-256", "")):
            return 401
        delivery = h.get("x-github-delivery", "")
        try:
            seen = self.conn.execute("SELECT 1 FROM baseline_jobs WHERE delivery_id=?", (delivery,)).fetchone()
            if seen:                                    # step 1: check ...
                return 200
            p = json.loads(body)
            if h.get("x-github-event") == "pull_request" and p.get("action") in {"opened", "synchronize",
                                                                                "reopened", "ready_for_review"}:
                pr = p["pull_request"]                  # step 2: ... then enqueue (not atomic with step 1)
                self.conn.execute("INSERT INTO baseline_jobs (delivery_id, repo, pr_number, head_sha) "
                                  "VALUES (?,?,?,?)", (delivery, p["repository"]["full_name"], pr["number"],
                                                       pr["head"]["sha"]))
            return 200
        except sqlite3.Error:
            return 500                                  # GitHub does not resend: this delivery is lost (F11)
