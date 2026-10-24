# Pre-registration: rung 1 (rule-based checks)

Written 24 Oct 2026, **before** rung 1 is run on the golden set. Commit this file first; the run comes after.
Why: if the rules were chosen after seeing results, they could be tuned to the 10 planted bugs, and rung 1 would look better than a real team's default setup.

## What rung 1 is
A static analyser (ruff) runs on each PR's head version. **Only warnings on lines the PR changed** become findings
(a reviewer comments on the change, not on old code). Each warning becomes a `Finding` with `agent_type=static`.

## Fixed choices
- **Tool:** ruff (the version is recorded in each result file). No LLM, no network.
- **Rule set** (what a reasonable team would switch on, chosen *without* looking at which planted bug each one catches):
  `F` (pyflakes: real errors), `E9` (syntax), `B` (bugbear: likely bugs), `S` (bandit: security),
  `DTZ` (timezone-naive dates), `BLE` (catch-all except), `PERF` (performance anti-patterns).
  Style rules (naming, line length, quotes) are **excluded**, because a reviewer doesn't post those as findings.
- **Severity mapping:** `S` → high, `B`/`DTZ`/`BLE` → medium, everything else → low. Confidence = 1.0 (a rule either fires or it doesn't).
- **Matching and metrics:** as in `GOLDEN_SET_PLAN.md` (same file, overlapping lines ±3). Precision over all findings
  on all 14 seeded PRs (clean ones included); recall over the 10 seeded problems. Real set: per-PR table (option A).

## Prediction (written before running, so it can be wrong in public)
Rung 1 should catch **S01** (SQL built from a string, rule S608) and **S06** (`date.today()`, rule DTZ011), and nothing else
of the planted ten: timing, path traversal, partial writes, N+1, tests and docs aren't things a linter can see.
Expected: **recall ≈ 2/10**, precision high. That gap is what rungs 2–4 have to close.
