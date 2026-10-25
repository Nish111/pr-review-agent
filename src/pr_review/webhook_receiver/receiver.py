"""The webhook receiver. Each defence is tagged with the failure it answers (F1..F17 in the ingress matrix).

Order of work for one request, and why:
  1. verify the signature on the RAW bytes (F1, F2), with old+new secret during rotation (F3)
  2. append the raw delivery to the inbox file BEFORE touching the database (F12 write-ahead log)
  3. ingest into the database; if the database fails, the delivery is still safe in the inbox and we
     still answer 202, because a failed reply means GitHub never resends it (F11, confirmed by Nishant)
Ingest itself never raises for bad input: malformed payloads go to the dead-letter table (F6).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

PR_ACTIONS = {"opened", "synchronize", "reopened", "ready_for_review"}          # F7 allow-list
MEMBER_ROLES = {"OWNER", "MEMBER", "COLLABORATOR"}                               # F17
REVIEW_COMMAND = "/review"
DAILY_COMMAND_LIMIT = 5                                                          # F17
BURST_PUSHES, BURST_WINDOW_S = 3, 600                                            # F10 (Nishant's answer)
SAFE_HEADERS = ("x-github-event", "x-github-delivery")                           # F15: nothing else is logged


@dataclass(frozen=True)
class Reply:
    status: int
    outcome: str


@dataclass
class Receiver:
    conn: sqlite3.Connection
    secrets: tuple[str, ...]                     # (current,) or (new, old) during a rotation window (F3)
    inbox: Path                                  # F12: append-only JSONL, one line per accepted delivery
    head_sha_of: Callable[[str, int], str] = field(default=lambda repo, pr: "")   # for /review comments
    clock: Callable[[], float] = time.time

    # ---------------------------------------------------------------- 1 · authenticity (F1, F2, F3)
    def signature_ok(self, body: bytes, header: str) -> bool:
        if not header or not header.startswith("sha256="):
            return False
        given = header.removeprefix("sha256=")
        return any(hmac.compare_digest(hmac.new(s.encode(), body, hashlib.sha256).hexdigest(), given)
                   for s in self.secrets if s)

    # ---------------------------------------------------------------- entry point
    def handle(self, headers: dict[str, str], body: bytes) -> Reply:
        h = {k.lower(): v for k, v in headers.items()}
        if not self.signature_ok(body, h.get("x-hub-signature-256", "")):
            self._event("ingress.rejected", {"reason": "bad_signature"})
            return Reply(401, "rejected: bad signature")
        delivery, event = h.get("x-github-delivery", ""), h.get("x-github-event", "")
        if not delivery or not event:
            return Reply(400, "missing delivery id or event header")
        try:                                                    # 2 · write-ahead (F12)
            with self.inbox.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"delivery": delivery, "event": event, "body": body.decode("utf-8", "replace"),
                                    "at": self.clock()}) + "\n")
        except OSError as e:
            return Reply(503, f"could not store delivery: {type(e).__name__}")   # nothing saved: honest failure
        try:                                                    # 3 · ingest
            outcome = self.ingest(delivery, event, body)
        except sqlite3.Error as e:
            self._safe_note(f"db unavailable, delivery kept in inbox: {type(e).__name__}")
            return Reply(202, "stored in inbox; database unavailable, will be drained")
        return Reply(200 if not outcome.startswith("accepted") else 202, outcome)

    # ---------------------------------------------------------------- ingest (also used by the inbox drain)
    def ingest(self, delivery: str, event: str, body: bytes) -> str:
        """One delivery = one transaction (F9). BEGIN IMMEDIATE takes the write lock first, so of 50 copies
        arriving at once exactly one sees "new delivery" and claims the work; a crash half-way leaves nothing."""
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            outcome = self._ingest(delivery, event, body)
        except BaseException:
            if self.conn.in_transaction:
                self.conn.execute("ROLLBACK")
            raise
        self.conn.execute("COMMIT")
        return outcome

    def _ingest(self, delivery: str, event: str, body: bytes) -> str:
        now = self.clock()
        if self.conn.execute("SELECT 1 FROM deliveries WHERE delivery_id=?", (delivery,)).fetchone():
            return "duplicate-delivery"                                         # F8 check 1 / F11 redelivery
        try:
            payload = json.loads(body)
            outcome = self._route(event, payload, delivery, now)
        except (ValueError, KeyError, TypeError) as e:                          # F6 schema drift
            self.conn.execute("INSERT INTO dead_letters (kind, ref, reason, payload, created_at) VALUES "
                              "('delivery', ?, ?, ?, ?)", (delivery, f"{type(e).__name__}: {e}"[:300],
                                                          body.decode("utf-8", "replace"), now))
            outcome = "dead-letter"
        try:
            self.conn.execute("INSERT INTO deliveries VALUES (?, ?, ?, ?)",
                              (delivery, event, _iso(now), outcome))
        except sqlite3.IntegrityError:
            return "duplicate-delivery"                                         # backstop; the lock prevents it
        self._event("ingress." + outcome.split(":")[0], {"delivery": delivery, "event": event, "outcome": outcome})
        return outcome

    def _route(self, event: str, p: dict, delivery: str, now: float) -> str:
        if event == "pull_request":
            return self._pull_request(p, delivery, now)
        if event == "issue_comment":
            return self._comment(p, delivery, now)
        return f"ignored:event {event}"

    def _pull_request(self, p: dict, delivery: str, now: float) -> str:
        action, pr, repo = p["action"], p["pull_request"], p["repository"]["full_name"]
        if action not in PR_ACTIONS:
            return f"ignored:action {action}"
        if pr.get("draft"):
            return "ignored:draft (comment /review to ask)"                    # F7, Nishant's answer
        if _is_bot(p.get("sender", {})):
            return "ignored:bot (comment /review to ask)"
        number, sha = int(pr["number"]), str(pr["head"]["sha"])
        fork = bool(pr["head"].get("repo", {}).get("fork")) or pr["head"].get("repo", {}).get("full_name") != repo
        if action == "synchronize" and self._burst(repo, number, sha, now):    # F10
            return "ignored:push burst (asked developer to comment /review)"
        return self._claim(repo, number, sha, delivery, "pull_request", fork, pr.get("title", ""), now)

    def _comment(self, p: dict, delivery: str, now: float) -> str:
        c, issue, repo = p["comment"], p["issue"], p["repository"]["full_name"]
        if p.get("action") != "created" or not str(c.get("body", "")).strip().startswith(REVIEW_COMMAND):
            return "ignored:not a /review command"
        if "pull_request" not in issue:
            return "ignored:comment on an issue, not a PR"
        number, author = int(issue["number"]), c["user"]["login"]
        day = _iso(now)[:10]

        def record(outcome: str) -> str:
            self.conn.execute("INSERT INTO commands (repo, pr_number, author, day, outcome) VALUES (?,?,?,?,?)",
                              (repo, number, author, day, outcome))
            return outcome

        if c.get("author_association") not in MEMBER_ROLES:                   # F17.1
            return record("ignored:/review by non-member")
        used = self.conn.execute("SELECT COUNT(*) FROM commands WHERE repo=? AND pr_number=? AND day=? AND "
                                 "outcome LIKE 'accepted%'", (repo, number, day)).fetchone()[0]
        if used >= DAILY_COMMAND_LIMIT:                                        # F17.3
            return record("ignored:/review daily limit reached")
        sha = self.head_sha_of(repo, number)
        if not sha:
            raise KeyError("could not resolve the PR head commit for /review")  # -> dead letter, replayable
        return record(self._claim(repo, number, sha, delivery, "review_command", False, issue.get("title", ""), now))

    # ---------------------------------------------------------------- the atomic claim (F8, F9) + supersede (F10)
    def _claim(self, repo: str, number: int, sha: str, delivery: str, trigger: str, fork: bool,
               title: str, now: float) -> str:
        key = f"{repo}#{number}@{sha}"
        try:
            self.conn.execute(
                "INSERT INTO jobs (work_key, repo, pr_number, head_sha, delivery_id, trigger, is_fork, "
                "untrusted_title, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (key, repo, number, sha, delivery, trigger, int(fork), title[:300], now))
        except sqlite3.IntegrityError:
            return "duplicate-work"                                             # same repo+PR+commit already claimed
        self.conn.execute("UPDATE jobs SET state='superseded' WHERE repo=? AND pr_number=? AND head_sha<>? "
                          "AND state IN ('queued','running')", (repo, number, sha))
        self._outbox("status", repo, number, sha, "Review queued.")           # F16 badge
        return "accepted"

    def _burst(self, repo: str, number: int, sha: str, now: float) -> bool:
        self.conn.execute("INSERT INTO pushes VALUES (?,?,?,?)", (repo, number, sha, now))
        n = self.conn.execute("SELECT COUNT(*) FROM pushes WHERE repo=? AND pr_number=? AND at>=?",
                              (repo, number, now - BURST_WINDOW_S)).fetchone()[0]
        if n < BURST_PUSHES:
            return False
        asked = self.conn.execute("SELECT 1 FROM outbox WHERE kind='ask' AND repo=? AND pr_number=? AND "
                                  "created_at>=?", (repo, number, now - BURST_WINDOW_S)).fetchone()
        if not asked:   # F16: one comment, never a stream of them
            self._outbox("ask", repo, number, sha, "Several pushes in a few minutes. When you're done, "
                         "comment /review and I'll review the latest commit.")
        return True

    # ---------------------------------------------------------------- helpers
    def _outbox(self, kind: str, repo: str, number: int, sha: str, text: str) -> None:
        self.conn.execute("INSERT INTO outbox (kind, repo, pr_number, head_sha, text, created_at) VALUES "
                          "(?,?,?,?,?,?)", (kind, repo, number, sha, text, self.clock()))

    def _event(self, name: str, detail: dict) -> None:
        self.conn.execute("INSERT INTO events (at, name, detail) VALUES (?,?,?)",
                          (self.clock(), name, json.dumps(detail, sort_keys=True)))

    def _safe_note(self, text: str) -> None:
        try:
            self._event("ingress.note", {"text": text})
        except sqlite3.Error:
            pass                                                                # the inbox already holds the delivery


def _is_bot(sender: dict) -> bool:
    return sender.get("type") == "Bot" or str(sender.get("login", "")).endswith("[bot]")


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")
