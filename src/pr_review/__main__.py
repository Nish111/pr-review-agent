"""Command line: python -m pr_review <command>."""

from __future__ import annotations

import argparse
import json
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
    e.add_argument("--rung", type=int, choices=[1, 2], required=True)
    e.add_argument("--click", help="path to a local clone of pallets/click (for the 5 real PRs)")
    e.add_argument("--provider", help="rung 2: groq | gemini | openrouter | ollama (key from env)")
    e.add_argument("--model", help="rung 2: exact model id, never defaulted (e.g. openai/gpt-oss-120b)")
    j = sub.add_parser("rightreason", help="right-reason check of location-matched findings")
    j.add_argument("action", choices=["judge", "handcheck", "compare"])
    j.add_argument("--rung", type=int, default=2)
    j.add_argument("--provider")
    j.add_argument("--model")
    args = parser.parse_args(argv)

    if args.cmd == "rightreason":
        from pr_review.evaluation import right_reason as rr
        if args.action == "judge":
            if not (args.provider and args.model):
                parser.error("judge needs --provider and --model (a different model from the reviewer)")
            out = rr.run_judge(ROOT, args.rung, args.provider, args.model)
            n = len(out["verdicts"])
            print(f"judged {n} matched finding(s) ({out['asked']} newly asked, rest reused); "
                  "verdicts saved, NOT printed (keeps the hand check independent)")
        elif args.action == "handcheck":
            print(f"wrote {rr.write_handcheck(ROOT, args.rung).relative_to(ROOT).as_posix()}")
        else:
            judge = {v["id"]: v["same_bug"] for v in json.loads(
                (ROOT / f"eval/results/rung{args.rung}_judge.json").read_text(encoding="utf-8"))["verdicts"]}
            hand = rr.read_handcheck(ROOT, args.rung)
            ids = sorted(set(judge) | set(hand), key=lambda x: int(x[1:]))
            agree = sum(1 for i in ids if judge.get(i) is not None and judge.get(i) == hand.get(i))
            for i in ids:
                print(f"{i}: hand={hand.get(i)} judge={judge.get(i)}")
            print(f"location-matched: {len(ids)}  right reason (hand): {sum(1 for i in ids if hand.get(i))}  "
                  f"right reason (judge): {sum(1 for i in ids if judge.get(i))}  agreement: {agree}/{len(ids)}")
        return 0

    if args.cmd == "eval":
        from pr_review.evaluation.run import print_report, rung1
        click = Path(args.click) if args.click else None
        if args.rung == 1:
            res = rung1(ROOT, click)
        else:
            if not (args.provider and args.model):
                parser.error("--rung 2 needs --provider and --model (the model id is never defaulted)")
            from pr_review.evaluation.run_llm import rung2
            res = rung2(ROOT, args.provider, args.model, click)
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
