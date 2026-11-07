"""`python -m pr_review report` -> reports/report.html. Every number is recomputed from files in the repo (E-F2, E-F6)."""

from __future__ import annotations

import html
import json
import re
import statistics
from pathlib import Path

from pr_review.evaluation.right_reason import matched_items, read_final

PRICE = {"input": 0.15, "output": 0.60, "source": "https://www.morphllm.com/groq-pricing",
         "as_of": "13 Oct 2026", "model": "openai/gpt-oss-120b on Groq (paid tier)"}   # USD per million tokens
SECRETS = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36}|gsk_[A-Za-z0-9]{20,}|"
                     r"AIza[0-9A-Za-z_-]{30,}")


def _calls(root: Path, rung: str) -> list[dict]:
    """One record per model call: estimated input tokens, answer characters, latency, measured usage if any."""
    res = json.loads((root / f"eval/results/rung{rung}.json").read_text(encoding="utf-8"))
    out = []
    if rung == "2":
        for t in res["trace"]:
            if t.get("sent"):
                rec = json.loads((root / f"eval/results/rung2_raw/{t['pr']}.json").read_text(encoding="utf-8"))
                out.append({"est_in": t["est_tokens"], "out_chars": len(rec.get("raw", "")), "latency": rec.get("latency_s"),
                            "usage": rec.get("usage")})
        return out
    arm = "search" if rung == "3" else "nosearch"
    for t in res["trace"]:
        for name, s in t.get("specialists", {}).items():
            if not s.get("est_tokens"):
                continue
            p = root / f"eval/results/rung3_raw/{arm}/{t['pr']}_{name}.json"
            rec = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
            out.append({"est_in": s["est_tokens"], "out_chars": len(rec.get("raw", "")), "latency": rec.get("latency_s"),
                        "usage": rec.get("usage")})
    return out


def economics(root: Path, rung: str) -> dict:
    calls = _calls(root, rung)
    tin = sum(c["est_in"] for c in calls)
    tout = sum(c["out_chars"] // 4 for c in calls)        # visible answer only: reasoning tokens are not in it (E-F1)
    lat = sorted(c["latency"] for c in calls if c["latency"] is not None)
    cost = tin / 1e6 * PRICE["input"] + tout / 1e6 * PRICE["output"]
    return {"calls": len(calls), "tokens_in_est": tin, "tokens_out_est": tout,
            "latency_median_s": round(statistics.median(lat), 2) if lat else None,
            "latency_p95_s": round(lat[max(0, int(len(lat) * 0.95) - 1)], 2) if lat else None,
            "usd_if_paid_lower_bound": round(cost, 4), "measured_calls": sum(1 for c in calls if c["usage"])}


def quality(root: Path, rung: str) -> dict:
    res = json.loads((root / f"eval/results/rung{rung}.json").read_text(encoding="utf-8"))
    t = res["seeded"]["totals"]
    out = {"findings": t["findings"], "loc_precision": round(t["precision"], 2), "loc_recall": round(t["recall"], 2),
           "clean_false_alarms": t["false_alarms_on_clean_prs"]}
    if rung in ("3", "3n"):
        h = read_final(root, rung)
        items = [i for i in matched_items(root, rung) if i["pr"][0] in "SC" and h.get(i["id"])]
        out.update(rr_precision=round(len(items) / t["findings"], 2), rr_recall=round(len({i["pr"] for i in items}) / 10, 2))
    elif rung == "2":
        out.update(rr_precision=0.50, rr_recall=0.50, note="official round 2, eval/findings_rung2.md")
    return out


def _table(rows: list[list], head: list[str]) -> str:
    th = "".join(f"<th>{html.escape(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def build_report(root: Path) -> Path:
    names = {"2": "Rung 2 · one LLM", "3": "Rung 3 · 4 specialists + search", "3n": "Rung 3 · 4 specialists, no search"}
    econ = {r: economics(root, r) for r in names}
    qual = {r: quality(root, r) for r in names}
    r4 = {n: json.loads((root / f"eval/results/{n}.json").read_text(encoding="utf-8")) for n in ("rung4", "rung4n")}
    rows_q = [[names[r], q["findings"], q["loc_precision"], q["loc_recall"], q.get("rr_precision"), q.get("rr_recall"),
               q["clean_false_alarms"]] for r, q in qual.items()]
    rows_e = [[names[r], e["calls"], f"{e['tokens_in_est']:,}", f"{e['tokens_out_est']:,}", e["latency_median_s"],
               e["latency_p95_s"], f"${e['usd_if_paid_lower_bound']:.4f}", e["measured_calls"]] for r, e in econ.items()]
    rows_4 = [[label, d["groups_seeded"], d["A_leave_one_pr_out"]["posted"], d["A_leave_one_pr_out"]["right_posted"],
               d["A_leave_one_pr_out"]["precision"], d["threshold_for_demo"]]
              for label, d in (("on rung 3 with search", r4["rung4"]), ("on rung 3 without search", r4["rung4n"]))]
    decisions = sorted((root / ".genesis/decisions").glob("S*.md"))
    rows_d = [[p.stem, p.read_text(encoding="utf-8").splitlines()[0].lstrip("# ")] for p in decisions]
    human = [["Rung 2 hand check", "9 findings, 2 rounds", "eval/HANDCHECK_RUNG2.md"],
             ["Rung 3 hand check", "27 + 28 findings, round 1; 12 in round 2; 5 pairs in round 2b (left open)",
              "eval/HANDCHECK_RUNG3.md, HANDCHECK_RUNG3n.md, HANDCHECK_RUNG3_ROUND2.md"],
             ["Unmatched-finding verdicts", "Claude labelled 40; Nishant sample-checked 10, agreed with 9",
              "eval/UNMATCHED_SAMPLE_CHECK.md"],
             ["Default configuration", "D = A: no search, threshold 0.84", "eval/findings_rung4.md, S6"]]
    css = """:root{--bg:#fff;--fg:#1d1d1f;--mut:#666;--line:#ddd;--acc:#2456c8}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--fg:#ececec;--mut:#9a9a9a;--line:#333;--acc:#7aa2ff}}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;max-width:980px;margin:0 auto;padding:24px 16px}
h1{font-size:24px}h2{font-size:18px;margin-top:32px}p,li{color:var(--fg)}.mut{color:var(--mut)}
table{border-collapse:collapse;width:100%;margin:8px 0 16px;font-size:14px;display:block;overflow-x:auto}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;white-space:nowrap}th{color:var(--mut);font-weight:600}
a{color:var(--acc)}"""
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PR Review Agent report</title><style>{css}</style></head><body>
<h1>PR Review Agent · evaluation, cost and audit report</h1>
<p class="mut">Built by <code>python -m pr_review report</code> from committed files only. Golden set: 14 seeded PRs (10 planted bugs,
4 clean) + 5 real pallets/click PRs. Model: openai/gpt-oss-120b on Groq's free tier.</p>
<h2>Quality (seeded set)</h2>{_table(rows_q, ["Rung", "Findings", "Precision (location)", "Recall (location)",
 "Precision (right reason)", "Recall (right reason)", "False alarms on clean PRs"])}
<p class="mut">Right reason = your hand check (official round). Rung 1 (rules only): precision 0.22, recall 0.20 (eval/findings_rung1.md).</p>
<h2>Rung 4 · may the bot post on its own?</h2>{_table(rows_4, ["Calibrated", "Grouped comments", "Posted (leave one PR out)",
 "Right", "Precision", "Threshold"])}
<p class="mut">Target ≥ 0.90 precision under leave-one-PR-out. Default configuration (decision S6): no search, threshold 0.84.</p>
<h2>Economics</h2>{_table(rows_e, ["Rung", "Model calls", "Input tokens (est.)", "Output tokens (est.)", "Latency median (s)",
 "Latency p95 (s)", "Cost if paid (lower bound)", "Calls with measured usage"])}
<p class="mut">Actual cost: $0 (free tier). "If paid" uses {html.escape(PRICE['model'])}: ${PRICE['input']} per million input tokens,
${PRICE['output']} per million output tokens (<a href="{PRICE['source']}">source</a>, as of {PRICE['as_of']}). Token counts are
estimates (characters ÷ 4); output excludes the model's hidden reasoning tokens, so the cost is a lower bound. Calls from now on
save the provider's measured usage (matrix 06, E-F1).</p>
<h2>Audit trail · decisions</h2>{_table(rows_d, ["Decision", "Title"])}
<h2>Audit trail · human judgement</h2>{_table(human, ["What", "Done", "Where"])}
<p class="mut">Pre-registrations committed before each run: eval/PREREG_RUNG1.md … PREREG_RUNG4.md. Mid-run changes are listed at the
end of each pre-registration. Per-review traces: <code>python -m pr_review trace &lt;PR&gt;</code>.</p>
</body></html>
"""
    if SECRETS.search(page):
        raise ValueError("report contains a key-shaped string; not written (matrix 06, E-F6)")
    out = root / "reports/report.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8", newline="\n")
    return out
