"""The "right reason" check (eval/PREREG_RUNG2.md, decision A AND B, run independently).

For every finding that matches a label by LOCATION, ask: does it describe the labelled bug?
  B: an AI judge (a different model from the reviewer) answers per finding  -> eval/results/rung<N>_judge.json
  A: Nishant answers by hand, WITHOUT seeing the judge's verdicts            -> eval/HANDCHECK_RUNG<N>.md
Then both are compared; their agreement is itself reported (the judge is an instrument that can fail).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pr_review.llm_client import complete as real_complete
from pr_review.specialists.single import _json_block, prompt_sha

JUDGE_PROMPT = "prompts/judge_right_reason.txt"


def matched_items(root: Path, rung: int) -> list[dict]:
    """Every location-matched finding, with the label(s) it matched. Stable order and ids (M1, M2...)."""
    res = json.loads((root / f"eval/results/rung{rung}.json").read_text(encoding="utf-8"))
    labels = {}
    for name in ("labels_seeded.json", "labels_real.json"):
        for pr in json.loads((root / "golden" / name).read_text(encoding="utf-8"))["prs"]:
            labels[pr["id"]] = pr.get("expected", [])
    from pr_review.evaluation.score import TOLERANCE
    items = []
    for part in ("seeded", "real"):
        for row in res[part]["prs"]:
            for f in row["findings"]:
                if not f.get("matched"):
                    continue
                hit = [lab for lab in labels[row["id"]] if lab["file_path"] == f["file"]
                       and f["lines"][0] <= lab["line_end"] + TOLERANCE
                       and f["lines"][1] >= lab["line_start"] - TOLERANCE]
                items.append({"id": f"M{len(items) + 1}", "pr": row["id"], "file": f["file"], "lines": f["lines"],
                              "summary": f["message"], "rationale": f.get("rationale", ""),
                              "label": "; ".join(sorted({lab.get("plain") or lab["description"] for lab in hit}))})
    return items


def run_judge(root: Path, rung: int, provider: str, model: str, complete=real_complete) -> dict:
    template = (root / JUDGE_PROMPT).read_text(encoding="utf-8")
    sha = prompt_sha(template)
    path = root / f"eval/results/rung{rung}_judge.json"
    if complete is real_complete:
        from pr_review.llm_client import pick_provider
        pick_provider(provider)       # a missing API key stops here, before recording N failed verdicts (1 Nov fix)
    # Reuse a verdict only if the same judge (model + prompt) already answered for the same finding text, and it
    # actually answered (same rule as the reviewer cache). Saves the judge's small daily quota (Gemini: 20/day).
    old = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    reuse = {}
    if old.get("model") == model and old.get("provider") == provider and old.get("prompt_sha") == sha:
        reuse = {v.get("key"): v for v in old.get("verdicts", []) if v.get("same_bug") is not None and v.get("key")}
    out = {"rung": rung, "provider": provider, "model": model, "prompt_sha": sha, "verdicts": [], "asked": 0}
    for it in matched_items(root, rung):
        key = f"{it['pr']}|{it['file']}|{it['lines'][0]}-{it['lines'][1]}|{it['summary']}"
        if key in reuse:
            out["verdicts"].append({**reuse[key], "id": it["id"]})
            continue
        out["asked"] += 1
        prompt = (template.replace("{label}", it["label"]).replace("{summary}", it["summary"])
                  .replace("{rationale}", it["rationale"]))
        try:
            data = json.loads(_json_block(complete(provider, model, prompt)))
            v = {"id": it["id"], "same_bug": bool(data["same_bug"]), "reason": str(data.get("reason", ""))}
        except Exception as e:  # noqa: BLE001 - an unanswered verdict is recorded as such, never guessed
            v = {"id": it["id"], "same_bug": None, "reason": f"judge failed: {type(e).__name__}: {e}"[:300]}
        out["verdicts"].append({**v, "key": key})
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return out


_HC_ENTRY = re.compile(r"^## M\d+ · PR (\S+) · `([^`]+)`.*?\*\*Reviewer said:\*\* (.*?)\n"
                       r".*?\*\*Your answer:\*\*[ \t]*([^\n]*)$", re.MULTILINE | re.DOTALL)


def _hc_key(it: dict) -> str:
    return f"{it['pr']}|{it['file']}:{it['lines'][0]}|{it['summary']}"


def write_handcheck(root: Path, rung: int) -> Path:
    """(Re)write the hand-check file. Answers already written are KEPT (matched by PR + location + summary),
    so regenerating after a re-score never wipes Nishant's work."""
    items = matched_items(root, rung)
    path = root / f"eval/HANDCHECK_RUNG{rung}.md"
    kept: dict[str, str] = {}
    if path.is_file():
        for m in _HC_ENTRY.finditer(path.read_text(encoding="utf-8")):
            if m.group(4).strip():
                kept[f"{m.group(1)}|{m.group(2)}|{m.group(3)}"] = m.group(4).strip()
    lines = [f"# Hand check: rung {rung} matched findings (right reason?)", "",
             "**What this is:** each finding below is in the right PLACE for a known bug. Your call: does it describe "
             "the SAME bug? Write `yes` or `no` (and a few words why, if you like) on each `Your answer` line.",
             f"**Do not open** `eval/results/rung{rung}_judge.json` before finishing; the AI judge's verdicts are kept "
             "out of this file on purpose, so your answers stay independent.", ""]
    for it in items:
        lines += [f"## {it['id']} · PR {it['pr']} · `{it['file']}:{it['lines'][0]}`", "",
                  f"- **Known bug:** {it['label']}", f"- **Reviewer said:** {it['summary']}",
                  f"- **Reviewer's reasoning:** {it['rationale']}",
                  "- **Your answer:** " + kept.get(_hc_key(it), ""), ""]
    if not items:
        lines.append("_No location-matched findings: nothing to check._")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


def read_handcheck(root: Path, rung: int) -> dict[str, bool | None]:
    text = (root / f"eval/HANDCHECK_RUNG{rung}.md").read_text(encoding="utf-8")
    out = {}
    # [ \t]* not \s*: an EMPTY answer must not swallow the next entry's heading (bug found 31 Oct on blank files)
    for m in re.finditer(r"^## (M\d+) .*?\*\*Your answer:\*\*[ \t]*([^\n]*)", text, re.MULTILINE | re.DOTALL):
        words = m.group(2).split()
        ans = words[0].lower().strip(".,;:") if words else ""
        out[m.group(1)] = True if ans.startswith("y") else False if ans.startswith("n") else None
    return out
