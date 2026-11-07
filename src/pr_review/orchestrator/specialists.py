"""Run the four specialists on one PR (matrix 04). Defences by tag: W1 a failed specialist leaves a partial review;
W2 shared token budget; W3 per-specialist cache (the caller's `ask`), quota stops the run; W5 exact duplicates
merged; W6 related chunks from changed files left out (by the caller); W7 grounding over shown code only; W8 strict
parse, no re-asking."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from pr_review.contracts import AgentType, Finding, Span
from pr_review.llm_client import QuotaExhausted
from pr_review.orchestrator.ratelimit import TokenBucket
from pr_review.specialists.single import MAX_PROMPT_TOKENS, WINDOW, build_context, estimate_tokens, parse_response

SPECIALISTS = (AgentType.SECURITY, AgentType.QUALITY, AgentType.TESTS, AgentType.DOCS)
OUTPUT_RESERVE = 1500          # tokens kept free per call for the answer (it counts towards the per-minute limit)
NO_CONTEXT = "(none)"
REVIEW_BUDGET = 20_000         # matrix 06, E-F3: estimated tokens (prompt + answer reserve) per review


@dataclass
class SpecialistResult:
    agent: AgentType
    ok: bool = False
    findings: list[Finding] = field(default_factory=list)
    dropped: list[dict] = field(default_factory=list)
    error: str = ""
    parse_error: str = ""
    est_tokens: int = 0
    waited_s: float = 0.0
    cached: bool = False
    context_mode: str = ""


def related_block(hits: list) -> tuple[str, list[Span]]:
    """Retrieved chunks as numbered code, each with its path and base line numbers (matrix 03 R10, R11)."""
    if not hits:
        return NO_CONTEXT, []
    blocks, spans = [], []
    for h in hits:
        lines = h.text.split("\n")
        body = "\n".join(f"{h.start_line + i:5d}  {ln}" for i, ln in enumerate(lines))
        blocks.append(f"=== {h.path} (lines {h.start_line}-{h.end_line}) ===\n{body}")
        spans.append(Span(h.path, h.start_line, h.end_line))
    return "\n\n".join(blocks), spans


def build_prompt(template: str, pr: dict, diff: str, tree: Path, changed: dict[str, set[int]],
                 related: str) -> tuple[str, list[Span], str]:
    """As rung 2 (whole files, then ±WINDOW, then ±10), with the related-code block included in the budget."""
    for window, mode in ((None, "whole-files"), (WINDOW, f"window-{WINDOW}"), (10, "window-10")):
        files, spans = build_context(tree, changed, window)
        prompt = (template.replace("{title}", pr.get("title", "")).replace("{body}", pr.get("body", ""))
                  .replace("{diff}", diff).replace("{files}", files).replace("{context}", related))
        if estimate_tokens(prompt) <= MAX_PROMPT_TOKENS:
            return prompt, spans, mode
    raise ValueError(f"PR {pr.get('id')} does not fit {MAX_PROMPT_TOKENS} tokens even with ±10 lines; not sent (S1)")


def merge_duplicates(findings: list[Finding]) -> tuple[list[Finding], list[dict]]:
    """W5: same file, overlapping lines, same category -> keep the higher confidence; record each merge."""
    kept: list[Finding] = []
    merges: list[dict] = []
    for f in sorted(findings, key=lambda x: -x.confidence):
        twin = next((k for k in kept if k.location.file_path == f.location.file_path and k.category == f.category
                     and k.location.line_start <= f.location.line_end
                     and f.location.line_start <= k.location.line_end), None)
        if twin is None:
            kept.append(f)
        else:
            merges.append({"kept": f"{twin.agent_type.value}:{twin.location.file_path}:{twin.location.line_start}",
                           "dropped": f"{f.agent_type.value}:{f.location.file_path}:{f.location.line_start}",
                           "category": f.category})
    kept.sort(key=lambda f: (f.location.file_path, f.location.line_start, f.category))
    return kept, merges


Ask = Callable[[AgentType, str], dict]      # (specialist, prompt) -> {"ok", "raw", "error", "cached"}


def review_pr(pr: dict, diff: str, tree: Path, changed: dict[str, set[int]], hits: list,
              templates: dict[AgentType, str], ask: Ask, bucket: TokenBucket,
              budget: int | None = None) -> dict:
    """All four specialists on one PR, in parallel within the shared budget. Never raises for one specialist's
    failure (W1); re-raises QuotaExhausted after the others finish, so the run can stop cleanly (W3)."""
    related, related_spans = related_block(hits)
    results = {a: SpecialistResult(a) for a in SPECIALISTS}
    quota: list[QuotaExhausted] = []

    def one(agent: AgentType) -> None:
        r = results[agent]
        try:
            prompt, spans, r.context_mode = build_prompt(templates[agent], pr, diff, tree, changed, related)
        except ValueError as e:
            r.error = str(e)
            return
        r.est_tokens = estimate_tokens(prompt)
        rec = ask(agent, prompt) if _cached_hint(ask, agent, prompt) else None
        if rec is None:
            r.waited_s = bucket.reserve(r.est_tokens + OUTPUT_RESERVE)
            try:
                rec = ask(agent, prompt)
            except QuotaExhausted as e:
                quota.append(e)
                r.error = "quota exhausted"
                return
        r.cached = bool(rec.get("cached"))
        if not rec.get("ok"):
            r.error = rec.get("error", "call failed")
            return
        parsed = parse_response(rec["raw"], spans + related_spans, agent)
        r.parse_error, r.dropped = parsed.parse_error, parsed.dropped
        r.findings, r.ok = parsed.findings, not parsed.parse_error

    # BudgetGuard (E-F3): specialists in priority order until the review budget is spent; the rest are skipped.
    allowed, spent = [], 0
    for agent in SPECIALISTS:
        try:
            est = estimate_tokens(build_prompt(templates[agent], pr, diff, tree, changed, related)[0]) + OUTPUT_RESERVE
        except ValueError:
            est = 0                                       # doesn't fit at all: `one` records why
        if budget is not None and spent + est > budget:
            results[agent].error = f"skipped: review budget {budget} tokens would be exceeded (BudgetGuard)"
            continue
        spent += est
        allowed.append(agent)
    with ThreadPoolExecutor(max_workers=len(SPECIALISTS)) as pool:
        list(pool.map(one, allowed))
    if quota:
        raise quota[0]
    merged, merges = merge_duplicates([f for r in results.values() for f in r.findings])
    done = [a.value for a, r in results.items() if r.ok]
    return {"findings": merged, "merges": merges, "completed": done, "partial": len(done) < len(SPECIALISTS),
            "specialists": results}


def _cached_hint(ask: Ask, agent: AgentType, prompt: str) -> bool:
    """True if `ask` can answer from its cache without a call (so no budget is reserved for it)."""
    probe = getattr(ask, "is_cached", None)
    return bool(probe and probe(agent, prompt))
