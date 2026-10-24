"""Command line: python -m pr_review <command>."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from pr_review.evaluation.golden import check

ROOT = Path(__file__).resolve().parents[2]


def _last_commit(path: Path) -> str:
    """Short hash of the last commit that touched `path`, read with git (run by the user)."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%h", "--", str(path)], cwd=ROOT,
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return "unknown (git not available)"
    return out.stdout.strip() or "NOT COMMITTED YET (labels must be committed before any scoring)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pr_review")
    sub = parser.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("golden", help="golden PR set")
    g.add_argument("action", choices=["check"])
    g.add_argument("--labels", nargs="+", default=["golden/labels_seeded.json", "golden/labels_real.json"])
    g.add_argument("--no-git", action="store_true", help="skip the commit-hash lookup")
    e = sub.add_parser("eval", help="run one rung over the golden set and score it")
    e.add_argument("--rung", type=int, choices=[1], required=True)
    e.add_argument("--click", help="path to a local clone of pallets/click (for the 5 real PRs)")
    args = parser.parse_args(argv)

    if args.cmd == "eval":
        import json

        from pr_review.evaluation.run import print_report, rung1
        res = rung1(ROOT, Path(args.click) if args.click else None)
        out = ROOT / "eval" / "results" / f"rung{args.rung}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print_report(res)
        print(f"saved {out.relative_to(ROOT).as_posix()}")
        return 0

    ok = True
    for rel in args.labels:
        labels = ROOT / rel
        r = check(labels, ROOT)
        print(f"{rel}: {r.total} PRs ({r.planted} with known problems, {r.clean} clean, {r.real} real), "
              f"{r.known_problems} known problems")
        if not args.no_git:
            print(f"  last committed in: {_last_commit(labels)}")
        for p in r.problems:
            print(f"  PROBLEM: {p}")
        ok = ok and r.ok
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
