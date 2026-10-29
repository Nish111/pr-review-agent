# Failure matrix 04 · Workflow & specialists

Draft v1, 27 Oct 2026. Same loop as matrices 01-03. The brief's group 4 is: *one job → 4 parallel specialists
(security, quality, tests, docs) → `Finding[]` each; checkpoint per node.*
The **baseline** is `pr-review-agent.html`: LangGraph fans out to 4 nodes in parallel, with checkpoints so a run can resume.

> **What you need to do in this file:** nothing to answer. Read it and push back on anything that looks wrong.

---

## What this component is (read this first)

Rung 2 was one reviewer doing everything. Rung 3 splits the job between four narrower reviewers, each with its own
instructions: **security**, **quality** (correctness and reliability), **tests**, and **docs**. Each one also gets the
related code that M5's search finds. The idea is the same as a human team: a narrow brief catches more in its area.

The orchestrator is the part that runs the four, collects what they say, and decides what to do when one fails.
Merging their findings properly (scoring them, removing overlaps, deciding what gets posted) is rung 4 (M7). Here we
only remove exact duplicates.

## 1 · Purpose and contract

- **In:** one review job (diff, changed files, the PR's base commit), the code index.
- **Out:** a `Review` with each specialist's findings, the list of specialists that **completed**, and `partial = true`
  if any did not. Every finding is grounded in lines the specialist was shown.
- **Invariants:** `every_posted_finding_is_grounded`; `every_outbound_call_is_bounded`; a partial review is never
  presented as complete (it goes to the approval queue, as `route()` already does since M1).

## 2 · Assumptions

| # | Assumption | If it is false |
|---|---|---|
| C1 | Four calls can run at the same moment | Groq allows 8,000 tokens per minute, and four 3,000-token calls are 12,000 → W2 |
| C2 | Every specialist finishes | one times out or returns junk → W1, W8 |
| C3 | The daily quota lasts the run | it runs out at PR 9, specialist 3 → W3 |
| C4 | Each specialist stays in its area | four reviewers each flag the same SQL injection, or the docs reviewer reviews security → W4, W5 |
| C5 | Line numbers mean one thing | retrieved code uses base line numbers, changed files use head line numbers → W6 |

## 3 · Failure modes

**W1 · One specialist fails.** *(operational · known-known)*
- **What goes wrong:** the tests reviewer times out, or its connection drops three times.
- **What we build:** the other three still count. The review lists who completed and is marked `partial`.
- **How we notice:** `partial` in the trace and the result; a "specialist failed" count per specialist.
- **What happens after:** a partial review goes to the approval queue, never straight to posting (M1's `route()`).

**W2 · Running four calls at once breaks the per-minute limit.** *(operational · unknown-known)*
- **What goes wrong:** the html fans out to four nodes in parallel. On Groq's free tier the four requests together go
  over 8,000 tokens a minute, so they fail with "rate limited" errors, and retries make it worse.
- **What we build:** one shared **token budget per minute** for all four (a "token bucket"). Each call reserves its
  estimated tokens before it starts and waits if the minute is full. The calls still run in parallel when they fit.
- **How we notice:** time spent waiting for the budget, per PR, in the trace; "rate limited" errors stay at 0.
- **What happens after:** a PR takes longer (up to about a minute) but every call goes through.

**W3 · The daily quota runs out mid-run.** *(cost · known-known)*
- **What goes wrong:** the free tier's 200,000 tokens a day (S1) runs out after specialist 2 of PR 12.
- **What we build:** the run stops cleanly (as rung 2 does), and each **specialist's** answer is cached separately, so
  re-running continues from specialist 3 of PR 12 without asking again for anything already answered. That is the
  html's "checkpoint per node", in files.
- **How we notice:** `stopped: daily quota exhausted at <PR>/<specialist>` in the result.
- **What happens after:** re-run after the quota resets.

**W4 · A specialist strays out of its area.** *(quality · known-unknown)*
- **What goes wrong:** the docs reviewer flags a SQL injection. That isn't harmful in itself, but it means the split isn't
  doing what it claims.
- **What we build:** nothing that blocks it; it is **measured**: each finding records which specialist raised it, and the
  report shows which specialist found each labelled bug.
- **How we notice:** the per-specialist table in the results.
- **What happens after:** if the split doesn't hold, that's a finding about rung 3, reported as such.

**W5 · Several specialists report the same problem.** *(cost + quality · known-known)*
- **What goes wrong:** security and quality both report the SQL injection, so a human reads it twice.
- **What we build (rung 3):** exact duplicates are removed: same file, overlapping lines, same category. The finding with
  the higher confidence stays, and the trace records the merge. Smarter merging is rung 4 (M7).
- **How we notice:** a "duplicates removed" count.
- **What happens after:** near-duplicates can remain until M7. Scoring counts each labelled bug once either way.

**W6 · A finding cites the right number in the wrong version of the file.** *(quality · unknown-known)*
- **What goes wrong:** changed files are shown at their **head** line numbers, retrieved code at **base** line numbers.
  If retrieval returned another part of a changed file, "line 40" could mean two different lines.
- **What we build:** retrieved chunks from files the PR changes are left out. The specialist already sees those files.
- **How we notice:** a "dropped: file already shown" count.
- **What happens after:** every citation has exactly one meaning, so grounding checks stay exact.

**W7 · A finding cites lines the specialist wasn't shown.** *(quality · known-known)*
- **What goes wrong:** the model invents `utils.py:88`.
- **What we build:** the same grounding check as rung 2, extended: evidence must lie in the shown changed lines **or** in a
  retrieved chunk (matrix 03, R11). Ungrounded findings are dropped, never repaired.
- **How we notice:** the "dropped: ungrounded" list per specialist in the trace.

**W8 · A specialist's answer is malformed.** *(engineering · known-known)*
- **What we build:** strict parsing (the rung 2 parser, including its fixed JSON-in-a-string bug), no re-asking for a better answer.
- **How we notice:** `parse_error` per specialist in the trace; that specialist counts as failed (W1).

**W9 · Instructions hidden in the code or the PR text.** *(security · known-unknown)*
- **What we build:** every prompt says the PR text and all code are data, never instructions; the bot can never
  approve (invariant). A planted-injection PR is added to the golden set at M7, when posting exists.

**W10 · Rung 3 costs four times as much.** *(cost · known-known)*
- **What we build:** the estimated tokens per specialist are logged; the 5,000-token cap applies to **each** call
  (S1), with retrieval limited to 1,500 tokens of it.
- **How we notice:** tokens per PR in the trace, rung 2 vs rung 3, in the findings write-up.

## 4 · Tests

| Test | What we do | Which failure | Pass means | Baseline should fail? |
|---|---|---|---|---|
| Z1 | one specialist raises an error | W1 | review has the other 3 specialists' findings, `partial = true`, routed to the queue | no (LangGraph also continues) |
| Z2 | 4 specialists × 3,000 tokens, fake clock | W2 | never more than 8,000 tokens reserved in any 60 s window | **yes**: plain parallel fan-out sends 12,000 at once |
| Z3 | quota runs out at specialist 3, then re-run | W3 | the re-run asks only specialists 3-4 | — |
| Z4 | two specialists return the same finding | W5 | one finding kept, one merge recorded | — |
| Z5 | a finding cites lines never shown | W7 | dropped and listed | — |
| Z6 | retrieval returns a chunk of a changed file | W6 | that chunk is not shown | — |
| Z7 | a cached answer from another prompt sha | W3 | re-asked, not reused (rung 2 cache rule) | — |

## 5 · Glossary

| Term | Meaning |
|---|---|
| **Specialist** | one of the four narrow reviewers: security, quality, tests, docs |
| **Orchestrator** | the code that runs the specialists, collects results and handles failures |
| **Fan-out** | starting several pieces of work at the same time from one job |
| **Partial review** | a review where at least one specialist didn't finish; never presented as complete |
| **Token bucket** | a counter of how many tokens may still be sent this minute; a call waits until enough are free |
| **TPM** | tokens per minute: Groq's free-tier speed limit (8,000) |
| **Checkpoint** | a saved intermediate result, so a stopped run can continue without redoing it |
| **Head / base version** | the file after the PR / the file before the PR |
| **LangGraph** | the library the html uses to run the specialists as a graph of steps |
