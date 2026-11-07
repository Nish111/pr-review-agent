"""One review, step by step, rebuilt from committed files (FAILURE_MATRIX_06_TRACE_COST.md). No model calls.

Every step is printed with a state (done, cached, failed, skipped, not sent): a missing step is shown as missing (E-F4).
Only allow-listed fields are printed: ids, paths, line numbers, counts, times, verdicts, short summaries (E-F6)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pr_review.aggregator import features, group_findings
from pr_review.contracts import AgentType
from pr_review.evaluation.golden import changed_lines
from pr_review.evaluation.run_rung4 import _key, truth
from pr_review.orchestrator.specialists import NO_CONTEXT, SPECIALISTS, build_prompt

ARM_FILES = {"nosearch": ("3n", "rung4n"), "search": ("3", "rung4")}


def _label(root: Path, pr_id: str) -> dict:
    for name in ("labels_seeded.json", "labels_real.json"):
        for pr in json.loads((root / "golden" / name).read_text(encoding="utf-8"))["prs"]:
            if pr["id"] == pr_id:
                return pr
    raise KeyError(f"no PR {pr_id} in the golden set")


def build_trace(root: Path, pr_id: str, arm: str = "nosearch") -> dict:
    rung, r4name = ARM_FILES[arm]
    res = json.loads((root / f"eval/results/rung{rung}.json").read_text(encoding="utf-8"))
    tr = next((t for t in res["trace"] if t["pr"] == pr_id), None)
    row = next((r for part in ("seeded", "real") for r in res[part]["prs"] if r["id"] == pr_id), None)
    pr = _label(root, pr_id)
    out: dict = {"pr": pr_id, "title": pr.get("title", ""), "arm": arm, "model": res["model"],
                 "provider": res["provider"], "prompt_sha": res["prompt_sha"], "steps": []}
    if tr is None or row is None:
        out["steps"].append({"step": "review", "state": "missing", "note": "this PR has no record in the run"})
        return out
    if "retrieval" in tr:
        r = tr["retrieval"]
        out["steps"].append({"step": "retrieval", "state": "done", "mode": r["mode"], "chunks": len(r["hits"]),
                             "tokens": r["tokens"], "names": r["names"][:8]})
    diff = (root / pr["diff"]).read_text(encoding="utf-8")
    tree = root / "golden/seeded/head" / pr_id if pr.get("source") != "real" else None
    for agent in SPECIALISTS:
        s = tr["specialists"].get(agent.value, {})
        cache = root / "eval/results/rung3_raw" / arm / f"{pr_id}_{agent.value}.json"
        rec = json.loads(cache.read_text(encoding="utf-8")) if cache.is_file() else {}
        err = s.get("error", "")
        state = ("skipped" if err.startswith("skipped") else "not sent" if "does not fit" in err
                 else "failed" if not s.get("ok") else "cached" if s.get("cached") else "done")
        step = {"step": f"specialist:{agent.value}", "state": state, "est_tokens": s.get("est_tokens"),
                "latency_s": rec.get("latency_s"), "http_requests": rec.get("http_requests"),
                "usage": rec.get("usage", {"measured": False}), "findings": s.get("findings"),
                "dropped": [d.get("reason", "")[:80] for d in s.get("dropped", [])], "error": s.get("error", "")[:160]}
        if arm == "nosearch" and tree is not None and tree.is_dir() and rec.get("input_sha"):   # E-F5
            tmpl = (root / f"prompts/rung3_{agent.value}.txt").read_text(encoding="utf-8")
            prompt = build_prompt(tmpl, pr, diff, tree, changed_lines(diff), NO_CONTEXT)[0]
            step["prompt_check"] = ("matches what the model saw"
                                    if hashlib.sha256(prompt.encode()).hexdigest()[:16] == rec["input_sha"]
                                    else "DOES NOT MATCH the saved fingerprint")
        out["steps"].append(step)
    out["steps"].append({"step": "merge", "state": "done", "exact_duplicates_removed": len(tr.get("merges", []))})
    r4 = root / f"eval/results/{r4name}.json"
    cal = json.loads(r4.read_text(encoding="utf-8")) if r4.is_file() else None
    labels = truth(root, rung)
    for g in group_findings(pr_id, row["findings"]):
        lead = g.lead
        feat = features(g)
        score = cal["calibration_table"].get(" / ".join(feat), {}).get("score") if cal else None
        thr = cal["threshold_for_demo"] if cal else None
        route = ("post" if thr is not None and score is not None and score >= thr and not row.get("partial")
                 else "approval queue")
        out["steps"].append({"step": "comment", "state": "done", "where": f"{lead['file']}:{lead['lines'][0]}",
                             "lead": lead.get("specialist"), "supporting": [f.get("specialist") for f in g.supporting],
                             "summary": lead["message"][:100], "features": " / ".join(feat), "score": score,
                             "threshold": thr, "route": route,
                             "human_label": labels.get(_key(pr_id, lead["file"], lead["lines"], lead["message"]))})
    return out


def render(t: dict) -> str:
    lines = [f"{t['pr']} · {t['title']}", f"  arm={t['arm']}  model={t['provider']}/{t['model']}"]
    for s in t["steps"]:
        head = f"  [{s['state']:>8}] {s['step']}"
        if s["step"].startswith("specialist:"):
            u = s["usage"]
            tok = (f"tokens in={u.get('input_tokens')} out={u.get('output_tokens')} (measured)" if u.get("measured")
                   else f"~{s['est_tokens']} tokens (estimated)")
            lines.append(f"{head}  {tok}  {s['latency_s']}s  findings={s['findings']}"
                         + (f"  dropped={len(s['dropped'])}" if s["dropped"] else "")
                         + (f"  prompt: {s['prompt_check']}" if s.get("prompt_check") else "")
                         + (f"  {s['error']}" if s["error"] else ""))
        elif s["step"] == "comment":
            lines.append(f"{head}  {s['where']}  lead={s['lead']} +{len(s['supporting'])}  score={s['score']}  "
                         f"-> {s['route']}  (human: {s['human_label']})  {s['summary'][:60]}")
        else:
            extra = {k: v for k, v in s.items() if k not in ("step", "state")}
            lines.append(f"{head}  {extra}")
    return "\n".join(lines)


__all__ = ["AgentType", "build_trace", "render"]
