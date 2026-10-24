# Rung 1 results: rule-based checks (seeded set)

Run 24 Oct 2026 by Nishant, after the pre-registration was committed (`a3f9a72`, `eval/PREREG_RUNG1.md`).
Raw output: `eval/results/rung1.json`.

## The numbers (official: pre-registered rules, unchanged)

| | Value |
|---|---|
| **Precision** | **0.22** (2 of 9 findings right) |
| **Recall** | **0.20** (2 of 10 planted problems found: S01, S06) |
| False alarms on the 4 clean PRs | 7 |

## Prediction vs result

- **Recall: predicted ≈ 2/10, got 2/10.** It caught exactly the two predicted: S01 (SQL from a string, rule S608) and S06 (`date.today()`, rule DTZ011). Correct.
- **Precision: predicted "high", got 0.22. Wrong.** That's the useful part of this result.

## Why precision collapsed: the 7 false alarms

Each was checked against the code (the pre-registered rule says unmatched findings are checked before being counted):

| PR | Finding | Verdict | Why |
|---|---|---|---|
| C02 ×2, C03 ×3, C04 ×1 | `S101` "use of assert" in `tests/…` | false alarm | `assert` is how pytest tests are written. The bandit rule is meant for production code, where `assert` can be switched off. |
| C01 | `S608` "possible SQL injection" in `notes_svc/tags.py:11` | false alarm | the query is built only from `?` placeholders (`",".join("?" ...)`); the values are passed separately. Safe, and it's moved code, not new code. |

*(These verdicts are Claude's, with the reason shown. If you disagree with any, mark it here and the numbers get recomputed.)*

## What this means

1. **A rule-based reviewer is noisy where it doesn't understand context.** 6 of 7 false alarms come from one rule firing in test files. That's the "almost-right problem" from the lecture's failure catalog: correct by its own rule, wrong in context.
2. **It's blind to 8 of 10 planted problems:** timing attacks, path traversal, partial writes, N+1 queries, time-zone logic beyond `date.today()`, tests and docs. These need understanding, not pattern matching. That's the job rungs 2–4 have to do.
3. **The baseline to beat is now fixed:** precision 0.22, recall 0.20.

## A post-hoc variant (reported, NOT the official baseline)

If `S101` is switched off in test files (a common team setting), precision becomes **2/3 = 0.67** with the same recall.
This is shown only to explain the result. It was chosen **after** seeing the data, so it doesn't replace the pre-registered number.
Any later comparison uses **0.22 / 0.20**.

## Still to run
The 5 real click PRs (needs a local copy of click; next step).
