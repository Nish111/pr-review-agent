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
    e.add_argument("--rung", type=int, choices=[1, 2, 3], required=True)
    e.add_argument("--arm", choices=["search", "nosearch"], default="search",
                   help="rung 3: with code search (official) or without (PREREG_RUNG3 D1)")
    e.add_argument("--embedder", default="bge", help="rung 3 search arm: bge (S2) | none")
    e.add_argument("--click", help="path to a local clone of pallets/click (for the 5 real PRs)")
    e.add_argument("--provider", help="rung 2: groq | gemini | openrouter | ollama (key from env)")
    e.add_argument("--model", help="rung 2: exact model id, never defaulted (e.g. openai/gpt-oss-120b)")
    j = sub.add_parser("rightreason", help="right-reason check of location-matched findings")
    j.add_argument("action", choices=["judge", "handcheck", "compare"])
    j.add_argument("--rung", default="2", choices=["2", "3", "3n"], help="3n = rung 3 without search")
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
    r4 = sub.add_parser("rung4", help="aggregator + calibrated threshold on rung 3's saved findings (no model calls)")
    r4.add_argument("--on", choices=["3", "3n"], default="3", help="3 = rung 3 with search (official), 3n = without")
    tc = sub.add_parser("trace", help="one review, step by step, rebuilt from the saved runs (no model calls)")
    tc.add_argument("pr", help="golden PR id, e.g. S01 or R4")
    tc.add_argument("--arm", choices=["nosearch", "search"], default="nosearch",
                    help="default = decision S6 (no search)")
    sub.add_parser("report", help="static HTML report: quality, cost, latency, audit trail -> reports/report.html")
    gt = sub.add_parser("gate", help="regression gate: candidate results vs the committed baseline (matrix 07)")
    gt.add_argument("candidate", help="a results file in the rung 3 format, e.g. eval/results/rung3n_new.json")
    gt.add_argument("--baseline", default="eval/results/rung3n.json")
    rc = sub.add_parser("recalibrate", help="report a new calibration from golden + queue labels; never applies it")
    rc.add_argument("--db", default=".pr_review/store.db")
    sv = sub.add_parser("serve", help="live demo: webhook receiver + review worker (M9_SETUP.md)")
    sv.add_argument("--port", type=int, default=8787)
    sv.add_argument("--db", default=".pr_review/store.db")
    qu = sub.add_parser("queue", help="list comments waiting for human approval")
    qu.add_argument("--db", default=".pr_review/store.db")
    qu.add_argument("action", nargs="?", choices=["list", "approve", "reject", "dispute"], default="list")
    qu.add_argument("item", nargs="?", type=int, help="queue item number (#id from the list)")
    qu.add_argument("--note", default="")
    args = parser.parse_args(argv)

    if args.cmd == "rung4":
        from pr_review.evaluation.run_rung4 import rung4
        res = rung4(ROOT, args.on)
        a, b = res["A_leave_one_pr_out"], res["B_in_sample"]
        print(f"rung 4 on rung {args.on}: {res['groups_seeded']} grouped comments on the seeded set")
        print(f"  A leave-one-PR-out (official): posted {a['posted']}, right {a['right_posted']}, "
              f"precision {a['precision']}, folds with no threshold {a['folds_without_threshold']}/{len(a['folds'])}")
        print(f"  B in-sample (optimistic): threshold {b['threshold']}, posted {b['posted']}, "
              f"precision {b['precision']}")
        for c in res["C_real_per_pr"]:
            print(f"  C {c['pr']}: score {c['score']} posted={c['posted']} right={c['right']}")
        out = ROOT / "eval" / "results" / f"rung4{'' if args.on == '3' else 'n'}.json"
        out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"saved {out.relative_to(ROOT).as_posix()}")
        return 0

    if args.cmd == "gate":
        from pr_review.evaluation.gate import gate
        r = gate(ROOT, json.loads((ROOT / args.baseline).read_text(encoding="utf-8")),
                 json.loads((ROOT / args.candidate).read_text(encoding="utf-8")))
        print(f"gate: {r['verdict'].upper()}  baseline {r['baseline']}  candidate {r['candidate']}")
        for x in r["reasons"]:
            print(f"  FAIL: {x}")
        for x in r["unlabelled_matched"][:20]:
            print(f"  needs a right-reason label: {x}")
        return 0 if r["verdict"] == "pass" else 1

    if args.cmd == "recalibrate":
        from pr_review.evaluation.gate import recalibrate
        r = recalibrate(ROOT, ROOT / args.db)
        out = ROOT / "eval/results/recalibration_report.json"
        out.write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8", newline="\n")
        a = r["leave_one_out"]
        print(f"labels by source: {r['sources']}")
        print(f"leave-one-out: posted {a['posted']}, right {a['right_posted']}, precision {a['precision']}; "
              f"threshold if applied: {r['threshold_if_applied']} (NOT applied: {r['note']})")
        print(f"saved {out.relative_to(ROOT).as_posix()}")
        return 0

    if args.cmd == "serve":
        from pr_review.live.server import run
        db = ROOT / args.db
        db.parent.mkdir(parents=True, exist_ok=True)
        run(db, db.with_name("inbox.jsonl"), args.port)
        return 0

    if args.cmd == "trace":
        from pr_review.trace import build_trace, render
        print(render(build_trace(ROOT, args.pr, args.arm)))
        return 0

    if args.cmd == "report":
        from pr_review.reports import build_report
        print(f"wrote {build_report(ROOT).relative_to(ROOT).as_posix()}")
        return 0

    if args.cmd == "queue":
        import sqlite3

        from pr_review.hitl import ApprovalQueue
        db = ROOT / args.db
        db.parent.mkdir(parents=True, exist_ok=True)
        q = ApprovalQueue(sqlite3.connect(db, isolation_level=None))
        if args.action in ("approve", "reject"):
            if args.item is None:
                parser.error("give the item number, e.g. `queue approve 3`")
            row = q.conn.execute("SELECT work_key, text FROM approvals WHERE id=?", (args.item,)).fetchone()
            if row is None:
                parser.error(f"no queue item #{args.item}")
            if args.action == "dispute":
                q.dispute(args.item, "nishant", args.note or "disputed")
                print(f"#{args.item} disputed (stored as a 'wrong' label for the next calibration)")
                return 0
            if args.action == "reject":
                q.reject(args.item, "nishant", args.note)
                print(f"#{args.item} rejected (stored as a 'wrong' label for the next calibration)")
                return 0
            import os

            from pr_review.github_client import GitHub
            repo, rest = row[0].split("#", 1)
            number = int(rest.split("@", 1)[0])
            GitHub(os.environ["GITHUB_APP_ID"], os.environ["GITHUB_APP_KEY_PATH"]).comment(
                repo, number, "**PR review bot** · approved by a human reviewer\n\n- " + row[1])
            q.approve(args.item, "nishant", args.note)
            print(f"#{args.item} approved and posted to {repo}#{number}")
            return 0
        items = q.pending()
        print(f"{len(items)} comment(s) waiting for approval" + ("" if items else " (nothing has been queued yet)"))
        for it in items:
            print(f"  #{it['id']} {it['work_key']} {it['where']} score={it['score']} age={it['age_h']}h"
                  f"{' STALE' if it['stale'] else ''}: {it['text'][:80]}")
        return 0

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
            failed = [v for v in out["verdicts"] if v.get("same_bug") is None]
            print(f"judged {n - len(failed)} of {n} matched finding(s) ({out['asked']} asked this run); "
                  "verdicts saved, NOT printed (keeps the hand check independent)")
            if failed:
                print(f"  {len(failed)} NOT answered (first reason: {failed[0]['reason'][:120]}); "
                      "run the same command again (after the quota resets, if that was the reason)")
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
        elif args.rung == 3:
            if not (args.provider and args.model):
                parser.error("--rung 3 needs --provider and --model (the model id is never defaulted)")
            from pr_review.evaluation.run_rung3 import rung3
            res = rung3(ROOT, args.provider, args.model, click, arm=args.arm, embedder_key=args.embedder)
        else:
            if not (args.provider and args.model):
                parser.error("--rung 2 needs --provider and --model (the model id is never defaulted)")
            from pr_review.evaluation.run_llm import rung2
            res = rung2(ROOT, args.provider, args.model, click)
        name = res["rung"] if args.rung == 3 else args.rung
        out = ROOT / "eval" / "results" / f"rung{name}.json"

        def scored(r: dict) -> int:
            return len(r["seeded"]["prs"]) + len(r["real"]["prs"])
        if res.get("stopped") and out.is_file() and scored(json.loads(out.read_text(encoding="utf-8"))) > scored(res):
            out = out.with_name(f"rung{name}_stopped.json")      # never replace a more complete result (30 Oct)
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
