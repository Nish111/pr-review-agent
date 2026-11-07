"""Run rung 2 (single LLM reviewer) over the golden set, with a resumable per-PR cache.

Cache rule (memory-project M4 lesson: a cached FAILURE was once reused as a success): a cached answer is
reused only if it succeeded AND was produced by the same prompt hash, provider and model. Anything else is
asked again. A spent daily quota stops the run cleanly; re-running continues where it stopped.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

from pr_review.evaluation.golden import changed_lines
from pr_review.evaluation.run import _click_tree, _row
from pr_review.evaluation.score import score_pr, totals
from pr_review.llm_client import QuotaExhausted, http_attempts
from pr_review.llm_client import complete as real_complete
from pr_review.specialists.single import build_prompt, estimate_tokens, parse_response, prompt_sha

PROMPT = "prompts/rung2_single.txt"
Completer = Callable[[str, str, str], str]


def _ask(cache: Path, key: dict, prompt: str, provider: str, model: str, complete: Completer) -> dict:
    if cache.is_file():
        old = json.loads(cache.read_text(encoding="utf-8"))
        if old.get("ok") and all(old.get(k) == v for k, v in key.items()):
            return {**old, "cached": True}
        if old.get("ok"):                     # a good answer to a DIFFERENT question: keep a copy, never lose it
            keep = cache.parent / "superseded" / f"{cache.stem}.{old.get('input_sha') or old.get('prompt_sha')}.json"
            keep.parent.mkdir(parents=True, exist_ok=True)
            if not keep.exists():
                keep.write_text(cache.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    before, t0 = http_attempts(), time.monotonic()
    rec = dict(key)
    try:
        rec.update(ok=True, raw=complete(provider, model, prompt), error="")
        from pr_review.llm_client import last_usage
        if complete is real_complete and last_usage():
            rec["usage"] = {**last_usage(), "measured": True}       # matrix 06, E-F1
    except QuotaExhausted:
        raise
    except Exception as e:  # noqa: BLE001 - recorded per PR, never turned into an empty success
        rec.update(ok=False, raw="", error=f"{type(e).__name__}: {e}"[:600])
    rec.update(latency_s=round(time.monotonic() - t0, 2), http_requests=http_attempts() - before)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return {**rec, "cached": False}


def rung2(root: Path, provider: str, model: str, click_repo: Path | None,
          complete: Completer = real_complete) -> dict:
    template = (root / PROMPT).read_text(encoding="utf-8")
    sha = prompt_sha(template)
    cache_dir = root / "eval/results/rung2_raw"
    seeded = json.loads((root / "golden/labels_seeded.json").read_text(encoding="utf-8"))["prs"]
    real = json.loads((root / "golden/labels_real.json").read_text(encoding="utf-8"))["prs"]
    out = {"rung": 2, "provider": provider, "model": model, "prompt": PROMPT, "prompt_sha": sha,
           "seeded": {"prs": []}, "real": {"reporting": "per-PR", "prs": [], "skipped": click_repo is None},
           "trace": [], "stopped": ""}
    scores = []
    jobs = [("seeded", pr, root / "golden/seeded/head" / pr["id"]) for pr in seeded]
    if click_repo is not None:
        wd = root / "eval/workdir"
        wd.mkdir(parents=True, exist_ok=True)
        jobs += [("real", pr, _click_tree(click_repo, pr["intro_commit"], wd)) for pr in real]
    for part, pr, tree in jobs:
        diff = (root / pr["diff"]).read_text(encoding="utf-8")
        changed = changed_lines(diff)
        tr = {"pr": pr["id"], "part": part}
        try:
            prompt, context, mode = build_prompt(template, pr, diff, tree, changed)
        except ValueError as e:
            tr.update(sent=False, error=str(e))
            out["trace"].append(tr)
            fs, parsed = [], None
        else:
            key = {"prompt_sha": sha, "provider": provider, "model": model}
            try:
                rec = _ask(cache_dir / f"{pr['id']}.json", key, prompt, provider, model, complete)
            except QuotaExhausted as e:
                out["stopped"] = f"daily quota exhausted at {pr['id']}: {str(e)[:200]}"
                out["trace"].append({**tr, "sent": False, "error": "quota exhausted"})
                break
            parsed = parse_response(rec["raw"], context) if rec["ok"] else None
            fs = parsed.findings if parsed else []
            tr.update(sent=True, cached=rec["cached"], context_mode=mode, est_tokens=estimate_tokens(prompt),
                      latency_s=rec.get("latency_s"), http_requests=rec.get("http_requests"),
                      call_ok=rec["ok"], error=rec.get("error", ""),
                      parse_error=parsed.parse_error if parsed else "",
                      dropped=parsed.dropped if parsed else [])
            out["trace"].append(tr)
        s = score_pr(pr, fs)
        row = _row(pr, s, fs)
        for f, rf in zip(fs, row["findings"], strict=True):
            rf.update(severity=f.severity.value, confidence=f.confidence, rationale=f.rationale)
        out[part]["prs"].append(row)
        if part == "seeded":
            scores.append(s)
    out["seeded"]["totals"] = totals(scores)
    return out
