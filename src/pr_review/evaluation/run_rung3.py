"""Run rung 3 (four specialists, with or without code search) over the golden set (eval/PREREG_RUNG3.md).

Arms: "search" (official: related code from the M5 index at the PR's base commit) and "nosearch" (same prompts,
related code = "(none)"). Results: eval/results/rung3.json and rung3n.json. Each specialist's answer is cached on its
own (matrix 04, W3), reused only if it succeeded with the same prompt sha, provider, model, arm and related code.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable
from pathlib import Path

from pr_review.contracts import AgentType
from pr_review.evaluation.golden import changed_lines
from pr_review.evaluation.run import _click_tree, _row
from pr_review.evaluation.run_llm import _ask
from pr_review.evaluation.score import matches, score_pr, totals
from pr_review.llm_client import QuotaExhausted
from pr_review.llm_client import complete as real_complete
from pr_review.orchestrator import SPECIALISTS, TokenBucket, review_pr
from pr_review.specialists.single import prompt_sha

ARMS = {"search": "3", "nosearch": "3n"}
Completer = Callable[[str, str, str], str]


class Asker:
    def __init__(self, cache_dir: Path, pr_id: str, base_key: dict, provider: str, model: str,
                 complete: Completer, shas: dict[AgentType, str]):
        self.cache_dir, self.pr_id, self.base_key = cache_dir, pr_id, base_key
        self.provider, self.model, self.complete, self.shas = provider, model, complete, shas

    def _key(self, agent: AgentType, prompt: str) -> tuple[Path, dict]:
        key = {**self.base_key, "prompt_sha": self.shas[agent],
               "input_sha": hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]}
        return self.cache_dir / f"{self.pr_id}_{agent.value}.json", key

    def is_cached(self, agent: AgentType, prompt: str) -> bool:
        path, key = self._key(agent, prompt)
        if not path.is_file():
            return False
        old = json.loads(path.read_text(encoding="utf-8"))
        return bool(old.get("ok")) and all(old.get(k) == v for k, v in key.items())

    def __call__(self, agent: AgentType, prompt: str) -> dict:
        path, key = self._key(agent, prompt)
        return _ask(path, key, prompt, self.provider, self.model, self.complete)


def _related(index, repo: str, diff: str, base: str, changed: dict) -> tuple[list, dict]:
    from pr_review.retrieval import for_diff
    res = for_diff(index, repo, diff, base)
    shown = [h for h in res.hits if h.path not in changed]            # matrix 04, W6
    where = [f"{h.path}:{h.start_line}-{h.end_line}" for h in shown]
    return shown, {"mode": res.mode, "names": res.names, "hits": where,
                   "dropped_changed_file": len(res.hits) - len(shown), "dropped_in_diff": res.dropped_in_diff,
                   "didnt_fit": res.didnt_fit, "tokens": sum(h.tokens for h in shown), "note": res.note}


def rung3(root: Path, provider: str, model: str, click_repo: Path | None, arm: str = "search",
          embedder_key: str = "bge", complete: Completer = real_complete, bucket: TokenBucket | None = None,
          index_db: Path | None = None, cache_dir: Path | None = None) -> dict:
    templates = {a: (root / f"prompts/rung3_{a.value}.txt").read_text(encoding="utf-8") for a in SPECIALISTS}
    shas = {a: prompt_sha(t) for a, t in templates.items()}
    bucket = bucket or TokenBucket()
    seeded = json.loads((root / "golden/labels_seeded.json").read_text(encoding="utf-8"))["prs"]
    real = json.loads((root / "golden/labels_real.json").read_text(encoding="utf-8"))["prs"]
    out = {"rung": ARMS[arm], "arm": arm, "provider": provider, "model": model,
           "prompt": "prompts/rung3_<specialist>.txt", "prompt_sha": {a.value: s for a, s in shas.items()},
           "seeded": {"prs": []}, "real": {"reporting": "per-PR", "prs": [], "skipped": click_repo is None},
           "trace": [], "stopped": "", "embedder": None}
    indexes: dict = {}
    e = None
    if arm == "search":
        from pr_review import embedder as emb
        try:
            e = emb.get(embedder_key)
        except ImportError:
            e = None                                                   # keyword-only, recorded below (R8)
        out["embedder"] = e.name if e else f"unavailable ({embedder_key}): keyword-only"

    def index_for(repo: str):
        """One index FILE per repo (fixed 30 Oct 2026): in a shared file, keyword ranking (bm25) and the vector
        search both depended on the other repo's chunks, so notes-svc retrieval changed once click was indexed."""
        if repo not in indexes:
            from pr_review.ingestion.index import Index
            base_db = index_db or root / "eval/workdir/rung3_index.db"
            db = base_db.with_name(f"{base_db.stem}_{repo.replace('/', '_')}{base_db.suffix}")
            db.parent.mkdir(parents=True, exist_ok=True)
            indexes[repo] = Index(sqlite3.connect(db, isolation_level=None), e)
        return indexes[repo]
    jobs = [("seeded", pr, root / "golden/seeded/head" / pr["id"], "notes-svc", root / "golden/seeded/base",
             "seeded-base") for pr in seeded]
    if click_repo is not None:
        wd = root / "eval/workdir"
        wd.mkdir(parents=True, exist_ok=True)
        for pr in real:
            head = _click_tree(click_repo, pr["intro_commit"], wd)
            base = _click_tree(click_repo, pr["intro_commit"] + "^", wd, name=f"click-{pr['intro_commit']}-base")
            jobs.append(("real", pr, head, "pallets/click", base, pr["intro_commit"] + "^"))
    scores = []
    print(f"rung 3 [{arm}]: {len(jobs)} PRs x 4 specialists; progress is printed per PR", flush=True)
    for part, pr, tree, repo, base_tree, base in jobs:
        diff = (root / pr["diff"]).read_text(encoding="utf-8")
        changed = changed_lines(diff)
        tr: dict = {"pr": pr["id"], "part": part}
        hits = []
        if arm == "search":
            index = index_for(repo)
            if index.commit_of(repo) != base:
                rep = index.refresh(repo, base_tree, base)             # incremental (matrix 02, I5-I7)
                tr["index_refresh"] = {"embedded": rep.embedded, "reused": rep.vectors_reused, "s": rep.seconds}
            hits, tr["retrieval"] = _related(index, repo, diff, base, changed)
        ask = Asker(cache_dir or root / "eval/results/rung3_raw" / arm, pr["id"],
                    {"provider": provider, "model": model, "arm": arm}, provider, model, complete, shas)
        try:
            rv = review_pr(pr, diff, tree, changed, hits, templates, ask, bucket)
        except QuotaExhausted as e:
            out["stopped"] = f"daily quota exhausted at {pr['id']}: {str(e)[:200]}"
            out["trace"].append({**tr, "error": "quota exhausted"})
            break
        tr.update(partial=rv["partial"], completed=rv["completed"], merges=rv["merges"], specialists={
            a.value: {"ok": r.ok, "cached": r.cached, "est_tokens": r.est_tokens, "waited_s": round(r.waited_s, 1),
                      "context_mode": r.context_mode, "error": r.error, "parse_error": r.parse_error,
                      "findings": len(r.findings), "dropped": r.dropped}
            for a, r in rv["specialists"].items()})
        out["trace"].append(tr)
        print(f"  [{arm}] {pr['id']} done: {len(rv['completed'])}/4 specialists"
              f"{' (PARTIAL)' if rv['partial'] else ''}, {len(rv['findings'])} finding(s)", flush=True)
        fs = rv["findings"]
        s = score_pr(pr, fs)
        row = _row(pr, s, fs)
        row["partial"] = rv["partial"]
        for f, rf in zip(fs, row["findings"], strict=True):
            rf.update(severity=f.severity.value, confidence=f.confidence, rationale=f.rationale,
                      specialist=f.agent_type.value)
        row["found_by"] = {lab["problem"] if "problem" in lab else pr["id"]: sorted(
            {f.agent_type.value for f in fs if matches(f, lab)}) for lab in pr.get("expected", [])}
        out[part]["prs"].append(row)
        if part == "seeded":
            scores.append(s)
    out["seeded"]["totals"] = totals(scores)
    return out
