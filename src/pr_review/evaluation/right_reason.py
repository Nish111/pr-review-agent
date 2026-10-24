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
                              "label": "; ".join(sorted({lab["description"] for lab in hit}))})
    return items


def run_judge(root: Path, rung: int, provider: str, model: str, complete=real_complete) -> dict:
    template = (root / JUDGE_PROMPT).read_text(encoding="utf-8")
    out = {"rung": rung, "provider": provider, "model": model, "prompt_sha": prompt_sha(template), "verdicts": []}
    for it in matched_items(root, rung):
        prompt = (template.replace("{label}", it["label"]).replace("{summary}", it["summary"])
                  .replace("{rationale}", it["rationale"]))
        try:
            data = json.loads(_json_block(complete(provider, model, prompt)))
            v = {"id": it["id"], "same_bug": bool(data["same_bug"]), "reason": str(data.get("reason", ""))}
        except Exception as e:  # noqa: BLE001 - an unanswered verdict is recorded as such, never guessed
            v = {"id": it["id"], "same_bug": None, "reason": f"judge failed: {type(e).__name__}: {e}"[:300]}
        out["verdicts"].append(v)
    path = root / f"eval/results/rung{rung}_judge.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return out


def write_handcheck(root: Path, rung: int) -> Path:
    items = matched_items(root, rung)
    lines = [f"# Hand check: rung {rung} matched findings (right reason?)", "",
             "**What this is:** each finding below is in the right PLACE for a known bug. Your call: does it describe "
             "the SAME bug? Write `yes` or `no` (and a few words why, if you like) on each `Your answer` line.",
             f"**Do not open** `eval/results/rung{rung}_judge.json` before finishing; the AI judge's verdicts are kept "
             "out of this file on purpose, so your answers stay independent.", ""]
    for it in items:
        lines += [f"## {it['id']} · PR {it['pr']} · `{it['file']}:{it['lines'][0]}`", "",
                  f"- **Known bug:** {it['label']}", f"- **Reviewer said:** {it['summary']}",
                  f"- **Reviewer's reasoning:** {it['rationale']}", "- **Your answer:** ", ""]
    if not items:
        lines.append("_No location-matched findings: nothing to check._")
    path = root / f"eval/HANDCHECK_RUNG{rung}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


def read_handcheck(root: Path, rung: int) -> dict[str, bool | None]:
    text = (root / f"eval/HANDCHECK_RUNG{rung}.md").read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"^## (M\d+) .*?\*\*Your answer:\*\*\s*(\S*)", text, re.MULTILINE | re.DOTALL):
        ans = m.group(2).strip().lower().strip(".,;:")
        out[m.group(1)] = True if ans.startswith("y") else False if ans.startswith("n") else None
    return out
