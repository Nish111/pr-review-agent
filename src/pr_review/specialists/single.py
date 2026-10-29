"""Rung 2: a single LLM reviewer (eval/PREREG_RUNG2.md).

One call per PR, temperature 0, no retries of the model's answer (a retry of a dropped connection is a
transport retry, handled in llm_client). Output is parsed strictly; anything malformed or ungrounded is
dropped and recorded, never repaired (invariant every_posted_finding_is_grounded).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from pr_review.contracts import AgentType, ContractError, Finding, Span

MAX_PROMPT_TOKENS = 5000        # S1 decision: stays under Groq's 8k tokens/minute per request
CHARS_PER_TOKEN = 4             # rough, deliberately pessimistic estimate; no tokenizer dependency
WINDOW = 30                     # lines of context either side of a changed hunk when trimming


def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN + 1


def prompt_sha(template: str) -> str:
    return hashlib.sha256(template.encode("utf-8")).hexdigest()[:12]


def _numbered(lines: list[str], lo: int, hi: int) -> str:
    return "\n".join(f"{n:5d}  {lines[n - 1]}" for n in range(lo, hi + 1))


def build_context(tree: Path, changed: dict[str, set[int]], window: int | None) -> tuple[str, list[Span]]:
    """Numbered head code for every changed file. window=None: whole files; else ±window around changes."""
    blocks, spans = [], []
    for path in sorted(changed):
        f = tree / path
        if not f.is_file() or not changed[path]:
            continue
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        if not lines:
            continue
        if window is None:
            ranges = [(1, len(lines))]
        else:
            ranges = []
            for n in sorted(changed[path]):
                lo, hi = max(1, n - window), min(len(lines), n + window)
                if ranges and lo <= ranges[-1][1] + 1:
                    ranges[-1] = (ranges[-1][0], max(hi, ranges[-1][1]))
                else:
                    ranges.append((lo, hi))
        body = "\n   ...\n".join(_numbered(lines, lo, hi) for lo, hi in ranges)
        blocks.append(f"=== {path} ===\n{body}")
        spans.extend(Span(path, lo, hi) for lo, hi in ranges)
    return "\n\n".join(blocks), spans


def build_prompt(template: str, pr: dict, diff: str, tree: Path,
                 changed: dict[str, set[int]]) -> tuple[str, list[Span], str]:
    """Fill the template within the token budget: whole files, then ±WINDOW, then ±10, else refuse."""
    for window, mode in ((None, "whole-files"), (WINDOW, f"window-{WINDOW}"), (10, "window-10")):
        files, spans = build_context(tree, changed, window)
        prompt = (template.replace("{title}", pr.get("title", "")).replace("{body}", pr.get("body", ""))
                  .replace("{diff}", diff).replace("{files}", files))
        if estimate_tokens(prompt) <= MAX_PROMPT_TOKENS:
            return prompt, spans, mode
    raise ValueError(f"PR {pr.get('id')} does not fit {MAX_PROMPT_TOKENS} tokens even with ±10 lines; "
                     "not sent (S1: a call over budget is trimmed, never sent)")


@dataclass
class Parsed:
    findings: list[Finding] = field(default_factory=list)
    dropped: list[dict] = field(default_factory=list)     # {reason, item}
    parse_error: str = ""


def _json_block(text: str) -> str:
    """The JSON object in a model answer.

    Fixed 24 Oct 2026 (eval/findings_rung2.md): the first version looked for a ``` fence FIRST, and rung 2's
    answer for S01 was valid JSON whose `suggestion` string itself contained a ```python code fence, so the
    extractor cut the object in half and a correct finding was thrown away. Now: whole text as JSON first; then
    the outermost {...}; a fenced block only as a last resort. Valid JSON is never rejected.
    """
    t = text.strip()
    for candidate in (t, t[t.find("{"):t.rfind("}") + 1] if "{" in t and "}" in t else ""):
        if candidate:
            try:
                json.loads(candidate)
                return candidate
            except ValueError:
                pass
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", t, re.DOTALL)
    return m.group(1) if m else t


def parse_response(text: str, context: list[Span], agent: AgentType = AgentType.SINGLE) -> Parsed:
    out = Parsed()
    try:
        data = json.loads(_json_block(text))
        items = data["findings"]
        if not isinstance(items, list):
            raise TypeError("'findings' is not a list")
    except (ValueError, KeyError, TypeError) as e:
        out.parse_error = f"{type(e).__name__}: {e}"
        return out
    for item in items:
        try:
            f = Finding.from_dict({**item, "agent_type": agent.value})
        except ContractError as e:
            out.dropped.append({"reason": f"contract: {e}", "item": item})
            continue
        if not f.is_grounded(context):
            out.dropped.append({"reason": "ungrounded: cites lines the reviewer was not shown", "item": item})
            continue
        out.findings.append(f)
    out.findings.sort(key=lambda f: (f.location.file_path, f.location.line_start, f.category))
    return out
