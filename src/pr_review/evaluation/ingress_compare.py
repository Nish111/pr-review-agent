"""Before/after numbers for ingress: the lecture design (BaselineReceiver) vs ours (Receiver), on the four
tests whose "baseline should fail?" column says yes in bold or names a missing part (matrix T7, T8, T10, T12).

Each scenario builds fresh throwaway databases in an OS temp folder (removed by Python when the run ends;
nothing in the repo is touched) and counts review jobs. Output: eval/results/ingress_compare.json.
T8 is a race, so it runs TRIALS times and reports every trial's job count, not one lucky run.
"""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path

from pr_review.job_queue import drain_inbox, sweep
from pr_review.store import connect
from pr_review.webhook_receiver import Receiver
from pr_review.webhook_receiver.baseline import BaselineReceiver
from pr_review.webhook_receiver.payloads import SECRET, pr_event, signed

TRIALS = 20
COPIES = 50


def _ours(d: Path) -> Receiver:
    return Receiver(connect(str(d / "store.db")), (SECRET,), d / "inbox.jsonl", clock=lambda: 1_761_000_000.0)


def _base(d: Path) -> BaselineReceiver:
    return BaselineReceiver(connect(str(d / "base.db")), SECRET)


def _count(conn, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def t7(d: Path) -> dict:
    """'opened' then 'ready for review' on the same commit: two deliveries, one piece of work."""
    ours, base = _ours(d), _base(d)
    for action in ("opened", "ready_for_review"):
        ours.handle(*signed(pr_event(action=action)))
        base.handle(*signed(pr_event(action=action)))
    return {"want": 1, "baseline_jobs": _count(base.conn, "baseline_jobs"), "ours_jobs": _count(ours.conn, "jobs")}


def _race(make, table: str, d: Path) -> int:
    h, body = signed(pr_event(), delivery="race-1")
    make(d)                                                 # create the schema before the threads start
    barrier = threading.Barrier(COPIES)

    def worker():
        r = make(d)
        barrier.wait()
        r.handle(h, body)

    threads = [threading.Thread(target=worker) for _ in range(COPIES)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return _count(connect(str(d / ("store.db" if table == "jobs" else "base.db"))), table)


def t8(root: Path) -> dict:
    """The same delivery 50 times at the same instant, repeated TRIALS times."""
    base, ours = [], []
    for i in range(TRIALS):
        (root / f"b{i}").mkdir()
        (root / f"o{i}").mkdir()
        base.append(_race(_base, "baseline_jobs", root / f"b{i}"))
        ours.append(_race(_ours, "jobs", root / f"o{i}"))
    return {"want": 1, "copies": COPIES, "trials": TRIALS, "baseline_jobs_per_trial": base,
            "ours_jobs_per_trial": ours, "baseline_trials_wrong": sum(1 for n in base if n != 1),
            "ours_trials_wrong": sum(1 for n in ours if n != 1)}


def t10(d: Path) -> dict:
    """The database is down while 20 webhooks arrive, then comes back."""
    ours, base = _ours(d), _base(d)
    ours.conn.close()
    base.conn.close()
    payloads = [signed(pr_event(number=n, sha=f"{n:040x}")) for n in range(1, 21)]
    ours_status = [ours.handle(*p).status for p in payloads]
    base_status = [base.handle(*p) for p in payloads]
    ours.conn, base.conn = connect(str(d / "store.db")), connect(str(d / "base.db"))
    drain_inbox(ours.inbox, ours.ingest)                    # ours replays its inbox; the baseline has none
    return {"want": 20, "baseline_replies": sorted(set(base_status)), "ours_replies": sorted(set(ours_status)),
            "baseline_jobs_after": _count(base.conn, "baseline_jobs"), "ours_jobs_after": _count(ours.conn, "jobs")}


def t12(d: Path) -> dict:
    """A webhook never arrives (GitHub got no reply, so it never resends). Only a sweeper can notice."""
    ours, base = _ours(d), _base(d)
    open_prs = [{"repo": "acme/notes-svc", "number": 9, "head_sha": "9" * 40, "draft": False}]
    sweep(ours.conn, open_prs, ours._claim, 1_761_000_000.0)
    return {"want": 1, "baseline_jobs": _count(base.conn, "baseline_jobs"), "ours_jobs": _count(ours.conn, "jobs"),
            "note": "the baseline has no sweeper, so nothing can recover the missing job"}


def run() -> dict:
    with tempfile.TemporaryDirectory(prefix="pr_review_ingress_") as tmp:
        root = Path(tmp)
        out = {}
        for name, fn in (("T7", t7), ("T10", t10), ("T12", t12)):
            (root / name).mkdir()
            out[name] = fn(root / name)
        (root / "T8").mkdir()
        out["T8"] = t8(root / "T8")
    return {"tests": {k: out[k] for k in ("T7", "T8", "T10", "T12")}}
