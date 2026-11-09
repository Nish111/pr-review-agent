"""M9 live path with fakes: webhook -> job -> specialists -> aggregator -> one comment + queue. No network."""

import base64
import json
from pathlib import Path

import pytest

from pr_review.job_queue import take
from pr_review.store import connect
from pr_review.webhook_receiver import Receiver
from pr_review.webhook_receiver.payloads import SECRET, pr_event, signed

ROOT = Path(__file__).resolve().parents[1]
HEAD = ROOT / "golden" / "seeded" / "head" / "S01"
pytest.importorskip("cryptography")


def test_app_jwt_is_signed_by_the_key():
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    from pr_review.github_client import app_jwt
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    tok = app_jwt("123", pem, now=1_000_000)
    head, body, sig = tok.split(".")
    pad = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))   # noqa: E731
    assert json.loads(pad(body)) == {"iat": 999_940, "exp": 1_000_540, "iss": "123"}
    key.public_key().verify(pad(sig), f"{head}.{body}".encode(), padding.PKCS1v15(), hashes.SHA256())   # raises if bad


class FakeGitHub:
    def __init__(self, diff, files):
        self.diff, self.files, self.comments, self.statuses = diff, files, [], []

    def pr(self, repo, n):
        return {"title": "Add note search by keyword", "body": "Search was slow", "head": {"sha": "a" * 40}}

    def pr_diff(self, repo, n):
        return self.diff

    def file(self, repo, path, ref):
        return self.files.get(path)

    def comment(self, repo, n, body):
        self.comments.append(body)

    def status(self, repo, sha, state, desc):
        self.statuses.append((state, desc))


@pytest.mark.skipif(not HEAD.is_dir(), reason="run golden/seeded/build.py first")
def test_live_review_posts_trusted_comment_and_queues_the_rest(tmp_path):
    from pr_review.hitl import ApprovalQueue
    from pr_review.live.worker import process
    from pr_review.orchestrator import TokenBucket
    lab = next(p for p in json.loads((ROOT / "golden/labels_seeded.json").read_text())["prs"] if p["id"] == "S01")
    diff = (ROOT / lab["diff"]).read_text(encoding="utf-8")
    files = {"notes_svc/notes.py": (HEAD / "notes_svc/notes.py").read_text(encoding="utf-8")}
    e = lab["expected"][0]

    def finding(cat, msg, conf=0.95, sev="high"):
        return {"severity": sev, "category": cat, "summary": msg, "file_path": e["file_path"],
                "line_start": e["line_start"], "line_end": e["line_end"], "confidence": conf,
                "rationale": "keyword is pasted into the SQL",
                "suggestion": "use ? placeholders",
                "evidence": [{"file_path": e["file_path"], "line_start": e["line_start"], "line_end": e["line_end"]}]}

    def fake_model(provider, model, prompt):
        if "SECURITY reviewer" in prompt:
            return json.dumps({"findings": [finding("sql-injection", "keyword interpolated into SQL")]})
        if "CORRECTNESS" in prompt:
            return json.dumps({"findings": [finding("unsafe-query", "SQL built with f-string")]})
        if "DOCUMENTATION" in prompt:
            return json.dumps({"findings": [{**finding("missing-doc", "README omits search details"),
                                             "file_path": "notes_svc/notes.py", "line_start": 1, "line_end": 1,
                                             "evidence": [{"file_path": "notes_svc/notes.py", "line_start": 1,
                                                           "line_end": 1}]}]})
        return '{"findings": []}'

    conn = connect(str(tmp_path / "s.db"))
    rx = Receiver(conn, (SECRET,), tmp_path / "inbox.jsonl")
    assert rx.handle(*signed(pr_event(sha="a" * 40))).status == 202
    job = take(conn, 1e12)
    gh = FakeGitHub(diff, files)
    s = process(conn, job, gh, fake_model, 1e12, bucket=TokenBucket(10**6))
    assert s["posted"] == 1 and s["queued"] == 1 and not s["partial"], s
    assert len(gh.comments) == 1 and "keyword interpolated into SQL" in gh.comments[0]
    assert "never approves or merges" in gh.comments[0] and "1 more comment(s) are waiting" in gh.comments[0]
    assert [st for st, _ in gh.statuses] == ["pending", "success"]
    assert len(ApprovalQueue(conn).pending()) == 1
    again = process(conn, job, FakeGitHub(diff, files), fake_model, 1e12, bucket=TokenBucket(10**6))
    assert again["posted"] == 0 and again["queued"] == 0                       # G11: a re-run posts nothing new
