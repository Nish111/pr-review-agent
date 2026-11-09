"""GitHub App client for the live demo (M9). Reads PRs and files, posts COMMENTS and commit statuses. Nothing else.

Invariant bot_never_approves_or_merges: this module has no call that approves a PR, requests changes as a
blocking review, or merges; tests/test_rung4.py (K7) searches the source to keep it that way. Every call has a
timeout (bounded calls)."""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

API = "https://api.github.com"
TIMEOUT_S = 20


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def app_jwt(app_id: str, key_pem: bytes, now: float | None = None) -> str:
    """The short-lived token that proves 'I am this App' (RS256, 9 minutes, per GitHub's App auth rules)."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    t = int(now if now is not None else time.time())
    head = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64(json.dumps({"iat": t - 60, "exp": t + 540, "iss": str(app_id)}, separators=(",", ":")).encode())
    key = serialization.load_pem_private_key(key_pem, password=None)
    sig = key.sign(f"{head}.{body}".encode(), padding.PKCS1v15(), hashes.SHA256())
    return f"{head}.{body}.{_b64(sig)}"


Transport = Callable[[str, str, dict, bytes | None], tuple[int, bytes]]


def _urllib(method: str, url: str, headers: dict, body: bytes | None) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


class GitHubError(RuntimeError):
    pass


class GitHub:
    def __init__(self, app_id: str, key_path: str | Path, transport: Transport = _urllib,
                 clock: Callable[[], float] = time.time):
        self.app_id, self.key = app_id, Path(key_path).read_bytes()
        self.transport, self.clock = transport, clock
        self._tokens: dict[str, tuple[str, float]] = {}            # repo -> (installation token, expires at)

    def _call(self, method: str, path: str, token: str, body: dict | None = None,
              accept: str = "application/vnd.github+json") -> bytes:
        headers = {"Authorization": f"Bearer {token}", "Accept": accept, "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "pr-review-agent"}
        data = json.dumps(body).encode() if body is not None else None
        if data is not None:
            headers["Content-Type"] = "application/json"
        status, raw = self.transport(method, API + path, headers, data)
        if status >= 400:
            raise GitHubError(f"{method} {path} -> HTTP {status}: {raw[:200]!r}")   # never includes the token
        return raw

    def token(self, repo: str) -> str:
        cached = self._tokens.get(repo)
        if cached and cached[1] > self.clock() + 60:
            return cached[0]
        jwt = app_jwt(self.app_id, self.key, self.clock())
        inst = json.loads(self._call("GET", f"/repos/{repo}/installation", jwt))["id"]
        tok = json.loads(self._call("POST", f"/app/installations/{inst}/access_tokens", jwt, {}))["token"]
        self._tokens[repo] = (tok, self.clock() + 50 * 60)        # GitHub's tokens last 1 hour; refresh early
        return tok

    def pr(self, repo: str, number: int) -> dict:
        return json.loads(self._call("GET", f"/repos/{repo}/pulls/{number}", self.token(repo)))

    def pr_diff(self, repo: str, number: int) -> str:
        return self._call("GET", f"/repos/{repo}/pulls/{number}", self.token(repo),
                          accept="application/vnd.github.diff").decode("utf-8", "replace")

    def file(self, repo: str, path: str, ref: str) -> str | None:
        try:
            return self._call("GET", f"/repos/{repo}/contents/{path}?ref={ref}", self.token(repo),
                              accept="application/vnd.github.raw").decode("utf-8", "replace")
        except GitHubError as e:
            if "HTTP 404" in str(e):
                return None                                       # deleted in this PR
            raise

    def comment(self, repo: str, number: int, body: str) -> None:
        """A normal PR conversation comment (the issues endpoint). Never a review verdict."""
        self._call("POST", f"/repos/{repo}/issues/{number}/comments", self.token(repo), {"body": body})

    def status(self, repo: str, sha: str, state: str, description: str) -> None:
        self._call("POST", f"/repos/{repo}/statuses/{sha}", self.token(repo),
                   {"state": state, "description": description[:140], "context": "pr-review-agent"})
