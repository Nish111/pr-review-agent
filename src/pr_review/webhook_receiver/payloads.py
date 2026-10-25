"""Builders for GitHub-shaped webhook payloads (field names as in GitHub's webhook docs; trimmed to what we read).
Used by the ingress tests and by `python -m pr_review ingress-compare`. The secret is a fake test value."""

import hashlib
import hmac
import json
import uuid

SECRET = "test-secret-not-real"


def pr_event(action="opened", number=7, sha="a" * 40, draft=False, sender="priya", sender_type="User",
             fork=False, repo="acme/notes-svc", title="Add note search"):
    head_repo = {"full_name": "stranger/notes-svc" if fork else repo, "fork": fork}
    return {"action": action, "repository": {"full_name": repo},
            "sender": {"login": sender, "type": sender_type},
            "pull_request": {"number": number, "draft": draft, "title": title,
                             "head": {"sha": sha, "repo": head_repo}}}


def comment_event(body="/review", number=7, role="MEMBER", login="priya", repo="acme/notes-svc", on_pr=True):
    issue = {"number": number, "title": "t"}
    if on_pr:
        issue["pull_request"] = {"url": "x"}
    return {"action": "created", "repository": {"full_name": repo}, "issue": issue,
            "comment": {"body": body, "author_association": role, "user": {"login": login}}}


def signed(payload, event="pull_request", delivery=None, secret=SECRET, raw=None):
    body = raw if raw is not None else json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return ({"X-Hub-Signature-256": sig, "X-GitHub-Event": event,
             "X-GitHub-Delivery": delivery or str(uuid.uuid4())}, body)
