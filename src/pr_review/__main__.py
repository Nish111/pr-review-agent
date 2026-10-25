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
    sub.add_parser("ingress-compare", help="before/after ingress numbers: lecture design vs ours (T7 T8 T10 T12)")
    ix = sub.add_parser("index", help="build or refresh the code index for one repo tree (matrix 02)")
    ix.add_argument("--repo", required=True, help="repo name, e.g. pallets/click")
    ix.add_argument("--path", required=True, help="folder holding the repo's files at one commit")
    ix.add_argument("--commit", required=True, help="the commit SHA that folder holds")
    ix.add_argument("--embedder", default="none", help="none (keyword only) | bge | jina | hash-64 (test only)")
    ix.add_argument("--db", default=".pr_review/index.db")
    se = sub.add_parser("search", help="search the code index (matrix 03)")
    se.add_argument("query")
    se.add_argument("--repo", help="repo name; default: the only indexed repo")
    se.add_argument("--embedder", default="none")
    se.add_argument("--k", type=int, default=5)
    se.add_argument("--db", default=".pr_review/index.db")
    ic = sub.add_parser("index-compare", help="before/after index numbers: html design vs ours (Y1, X2-X4)")
    ic.add_argument("--tree", required=True, help="a repo folder, e.g. eval/workdir/click-c69643b")
    args = parser.parse_args(argv)

    if args.cmd in ("index", "search"):
        import sqlite3

        from pr_review import embedder as emb
        from pr_review.ingestion.index import Index
        from pr_review.retrieval import search
        db = ROOT / args.db
        db.parent.mkdir(parents=True, exist_ok=True)
        index = Index(sqlite3.connect(db, isolation_level=None), emb.get(args.embedder))
        if args.cmd == "index":
            rep = index.refresh(args.repo, Path(args.path), args.commit)
            for k, v in vars(rep).items():
                print(f"{k:<18} {dict(v) if hasattr(v, 'most_common') else v}")
            return 0
        repos = [r[0] for r in index.conn.execute("SELECT DISTINCT repo FROM index_files")]
        repo = args.repo or (repos[0] if len(repos) == 1 else None)
        if repo is None:
            parser.error(f"--repo needed; indexed repos: {repos or 'none'}")
        res = search(index, repo, args.query, k=args.k)
        print(f"mode: {res.mode}  repo: {repo}  names: {res.names}  {res.note}")
        for h in res.hits:
            print(f"  {h.path}:{h.start_line}-{h.end_line}  {h.symbol or '-'}  [{'+'.join(h.lanes)}]")
        return 0

    if args.cmd == "index-compare":
        from pr_review.evaluation.index_compare import run as index_run
        res = index_run(ROOT / args.tree)
        y = res["Y1_exact_name_top5"]
        print(f"Y1 exact name in top {5}: baseline {y['baseline_hits']}/{y['names']} ({y['baseline_rate']}), "
              f"ours {y['ours_hits']}/{y['names']} ({y['ours_rate']})")
        for k in ("X2_X3_ghost_chunks", "X4_embeddings_after_one_line_edit"):
            print(f"{k}: {res[k]}")
        out = ROOT / "eval" / "results" / "index_compare.json"
        out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"saved {out.relative_to(ROOT).as_posix()}")
        return 0

    if args.cmd == "ingress-compare":
        from pr_review.evaluation.ingress_compare import run
        res = run()
        for name, r in res["tests"].items():
            shown = {k: v for k, v in r.items() if k != "note"}
            print(f"{name}: {shown}")
        out = ROOT / "eval" / "results" / "ingress_compare.json"
        out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"saved {out.relative_to(ROOT).as_posix()}")
        return 0

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
