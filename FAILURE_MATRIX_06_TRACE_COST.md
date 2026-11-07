# Failure matrix 06 · Data, proof & economics (traces, cost, audit)

Draft v1, 7 Nov 2026. Same loop as matrices 01-05. The brief's group 6: *every span / LLM call / cost / decision appended to
`agent_events`; a BudgetGuard blocks over-budget work.*
The **baseline** is `pr-review-agent.html`: an events table in Tiger/Timescale with continuous aggregates for cost and health.

> **What you need to do in this file:** nothing to answer. Read it and push back on anything that looks wrong.

---

## What this component is (read this first)

Every earlier milestone produced numbers. This component makes them **checkable**: for any review, anyone can see what was
asked, of which model, with which prompt version, how long it took, what it cost, what was dropped and why, and which human
decided what. It also stops the system spending more than it should. Without it, "rung 4 posts 8 of 8 correctly" is a claim;
with it, it's a trace someone can replay.

## 1 · Purpose and contract

- **In:** the records every step already writes: ingress events (M4), retrieval results (M5), each specialist call (M6 cache files), grouping, scores and routes (M7), approval-queue decisions.
- **Out:** `python -m pr_review trace <PR>`: one review, step by step. `python -m pr_review report`: a static HTML page with cost, latency and quality per rung.
- **Invariants:** no secret ever appears in a trace (ingress F15); every number in the report can be recomputed from committed files.

## 2 · Assumptions

| # | Assumption | If it is false |
|---|---|---|
| E1 | We know how many tokens each call used | so far only **estimates** were saved (characters ÷ 4) → E-F1 |
| E2 | Cost is zero, so it doesn't matter | the free tier hides what a paid run would cost; the brief asks for the economics → E-F2 |
| E3 | Each call stays within budget | a large PR × 4 specialists can blow a day's quota in one review → E-F3 |
| E4 | Records are complete | a crashed or stopped run leaves gaps that look like "nothing happened" → E-F4 |
| E5 | The trace shows what the model saw | the prompt text isn't stored, only its fingerprint → E-F5 |

## 3 · Failure modes

**E-F1 · Token counts are guesses.** *(proof · known-known; true of every run so far)*
- **What goes wrong:** every saved token number is an estimate (characters ÷ 4), deliberately pessimistic. gpt-oss also spends hidden
  "reasoning" tokens that are billed as output but never appear in the answer.
- **What we build:** from now on, the provider's own **usage** numbers (input, output, reasoning tokens) are saved with each call.
  Past runs keep their estimates, labelled as estimates.
- **How we notice:** the report says "measured" or "estimated" next to every token figure.

**E-F2 · "Free" hides the real cost.** *(economics · known-known)*
- **What we build:** the report shows what each rung **would** cost on Groq's paid tier: $0.15 per million input tokens and $0.60 per million output
  tokens for `openai/gpt-oss-120b` ([morphllm.com, Groq pricing, updated 13 Oct 2026](https://www.morphllm.com/groq-pricing)). Price and date are
  shown with the number, so a reader knows when to re-check them.

**E-F3 · One review spends too much.** *(cost · known-unknown)*
- **What we build:** a **BudgetGuard** per review: if the four specialists' estimated tokens exceed the review budget (default 20,000), the
  specialists run in a fixed priority order (security, quality, tests, docs) until it's spent; the rest are skipped and the review is **partial**,
  so it goes to a human (M1 `route()`).
- **How we notice:** `budget: skipped docs` in the trace.

**E-F4 · Gaps look like silence.** *(proof · known-known)*
- **What we build:** the trace shows every step with a state: done, cached, failed (with the error), skipped (with the reason), not sent (over budget). A missing step is printed as missing, never omitted.

**E-F5 · The trace can't show the prompt.** *(proof · known-unknown)*
- **What goes wrong:** only `prompt_sha` (the template's fingerprint) and `input_sha` (the full prompt's) are saved, not the text.
- **What we build:** the trace rebuilds the prompt from the committed template, diff and retrieval record, and checks its fingerprint
  against the saved `input_sha`. A match proves the trace shows what the model actually saw.

**E-F6 · A secret leaks into a trace or the report.** *(security · known-known)*
- **What we build:** the trace and report print only fields from an allow-list (ids, file paths, line numbers, counts, times, verdicts, short summaries), the same rule as ingress F15. A test scans the report for key-shaped strings.

## 4 · Tests

| Test | Failure | Pass means |
|---|---|---|
| V1 | E-F1 | a fake provider response with `usage` is saved with the call |
| V2 | E-F3 | 4 specialists × 6,000 tokens with a 20,000 budget → 3 run, docs skipped, review partial |
| V3 | E-F4 | a failed and a skipped specialist both appear in the trace, with reasons |
| V4 | E-F5 | the rebuilt prompt for a seeded PR matches its saved `input_sha` |
| V5 | E-F6 | the report contains no key-shaped string |
| V6 | E-F2 | the report's cost for rung 2 equals tokens × the stated price, recomputed in the test |

## 5 · Glossary

| Term | Meaning |
|---|---|
| **Trace** | the step-by-step record of one review |
| **Span** | one step in a trace (a retrieval, one specialist call, the routing decision) |
| **Usage** | the token counts the provider reports for a call (input, output, reasoning) |
| **Reasoning tokens** | tokens a reasoning model spends "thinking"; billed but not shown in the answer |
| **BudgetGuard** | the check that stops a review spending more than its token budget |
| **Audit trail** | the record of who decided what, and when (approvals, rejections, disputes, the decisions S1-S6) |
