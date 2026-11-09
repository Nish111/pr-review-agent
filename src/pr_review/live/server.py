"""`python -m pr_review serve`: the webhook endpoint (M4 Receiver) + one worker thread. Standard library HTTP server."""

from __future__ import annotations

import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pr_review.job_queue import complete as job_done
from pr_review.job_queue import fail, take
from pr_review.store import connect
from pr_review.webhook_receiver import Receiver

MAX_BODY = 5_000_000


def run(db: Path, inbox: Path, port: int = 8787, poll_s: float = 2.0) -> None:
    from pr_review.github_client import GitHub
    from pr_review.live.worker import process
    from pr_review.llm_client import complete
    gh = GitHub(os.environ["GITHUB_APP_ID"], os.environ["GITHUB_APP_KEY_PATH"])
    env = (os.environ.get("GITHUB_WEBHOOK_SECRET"), os.environ.get("GITHUB_WEBHOOK_SECRET_OLD"))
    secrets = tuple(s for s in env if s)
    if not secrets:
        raise SystemExit("GITHUB_WEBHOOK_SECRET is not set (M9_SETUP.md, step 5)")
    rx_conn = connect(str(db))
    rx = Receiver(rx_conn, secrets, inbox, head_sha_of=lambda repo, n: gh.pr(repo, n)["head"]["sha"])
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - http.server's naming
            n = int(self.headers.get("Content-Length", "0"))
            if self.path != "/webhook" or n > MAX_BODY:
                self.send_response(404 if self.path != "/webhook" else 413)
                self.end_headers()
                return
            body = self.rfile.read(n)
            with lock:
                reply = rx.handle(dict(self.headers), body)
            self.send_response(reply.status)
            self.end_headers()
            self.wfile.write(reply.outcome.encode()[:200])
            print(f"webhook {self.headers.get('X-GitHub-Event')} -> {reply.status} {reply.outcome}", flush=True)

        def do_GET(self):  # noqa: N802
            self.send_response(200 if self.path == "/health" else 404)
            self.end_headers()

        def log_message(self, *a):            # quiet: our own one-line log above, never headers (F15)
            pass

    def worker():
        conn = connect(str(db))
        while True:
            job = take(conn, time.time())
            if job is None:
                time.sleep(poll_s)
                continue
            print(f"review started: {job['work_key']}", flush=True)
            try:
                s = process(conn, job, gh, complete, time.time())
                job_done(conn, job["id"])
                print(f"review done: {s['posted']} posted, {s['queued']} queued, partial={s['partial']}", flush=True)
            except Exception as e:  # noqa: BLE001 - retried with backoff, then dead-lettered (F14)
                outcome = fail(conn, job["id"], str(e), time.time())
                print(f"review failed: {type(e).__name__}: {str(e)[:160]} -> {outcome}", flush=True)

    threading.Thread(target=worker, daemon=True).start()
    print(f"listening on http://localhost:{port}/webhook (Ctrl+C to stop)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
