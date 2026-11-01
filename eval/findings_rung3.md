# Rung 3 results: four specialists, with and without code search

> **DRAFT, 1 Nov 2026.** Uses your **round 1** hand check. Final after (1) the judge's last 6 verdicts and (2) round 2,
> where you see every disagreement with the judge plus three answers Claude flagged. Numbers marked † may change in round 2.

Runs: 29-31 Oct 2026, model `openai/gpt-oss-120b` on Groq, prompts as pre-registered (`eval/PREREG_RUNG3.md`).
Raw answers: `eval/results/rung3_raw/`; scores: `eval/results/rung3.json` (with search, official) and `rung3n.json` (without).
Two retrieval bugs were found and fixed mid-run; see the pre-registration's last section. No official answer used leaked context.

## 1 · Headline (seeded set, 14 PRs)

| | Rung 2 (one LLM) | **Rung 3, with search (official)** | Rung 3, without search |
|---|---|---|---|
| Findings | 10 | **50** | 29 |
| Recall, location | 0.70 | **1.00** (10/10) | 0.90 (9/10; S10 missed) |
| Precision, location | 0.70 | **0.46** (23/50) | 0.66 (19/29) |
| False alarms on the 4 clean PRs | 0 | **6** | 2 |
| **Recall, right reason** (your hand check) | 0.50 | **1.00** † (10/10) | 0.90 † (9/10) |
| **Precision, right reason** | 0.50 | **0.36** † (18/50) | 0.55 † (16/29) |
| Estimated prompt tokens, seeded set | ~16,000 | ~171,000 | ~69,000 |

**In one sentence:** rung 3 finds every planted bug for the right reason, but at the cost of many more comments. With search, almost two in three comments don't match a known bug, and the docs reviewer is the main source.

## 2 · What each change did

- **Splitting into specialists (rung 2 → rung 3 without search):** right-reason recall 0.50 → 0.90, precision 0.50 → 0.55,
  false alarms on clean PRs 0 → 2. The split found S05 (N+1 queries), S07 (missing test), S08 (weakened test) and S09, which rung 2 missed,
  without making precision worse. **This is the change that earned its place.**
- **Adding code search (without → with):** +1 bug (S10, the CLI help text that's now wrong), but +21 findings, of which 4 more are
  false alarms on clean PRs, and right-reason precision 0.55 → 0.36. The extra comments are mostly the **docs reviewer**
  (12 → 26 findings): seeing the README and other files, it flags "not documented" everywhere, including on clean PRs (C01, C03).
- **So for the vector lane (matrix 03, R5) and search in general:** on this golden set, search buys one bug for a large precision cost.
  It doesn't earn its place as is. The fix belongs in rung 4 (M7): an aggregator that scores, merges and filters findings,
  most obviously the docs reviewer's "not documented" comments, before anything is posted.

## 3 · Which specialist found what (right reason, round 1 †)

| Bug | with search | without search |
|---|---|---|
| S01 SQL injection | security, tests | security, tests |
| S02 timing attack | security, tests | security, quality |
| S03 path traversal | security, quality | security, quality |
| S04 partial write | quality, tests | quality |
| S05 N+1 queries | quality | quality, docs |
| S06 UTC vs local date | quality, tests | quality |
| S07 missing test | tests | quality, security |
| S08 weakened test | quality, tests | quality, tests |
| S09 README now wrong | docs, quality, security | docs, tests |
| S10 CLI help now wrong | docs | — |

The planned split mostly held: security found S01-S03 and quality found S04-S06. The **tests** reviewer also re-reported many
bugs as "and no test covers it", which is why it appears on S01-S06. That's a real but redundant signal: one bug, two comments.

## 4 · Real click PRs (per PR, no percentage; right reason, round 1 †)

| PR | Rung 2 | Rung 3 with search | Rung 3 without search |
|---|---|---|---|
| R1 colour codes in prompts | missed | **found** (tests) | **found** (quality, tests) |
| R2 pager temp file | not sent | not sent (too large, as pre-registered) | not sent |
| R3 fish completion | found | located, but your hand check said wrong reason | **found** (tests) |
| R4 EOFError on the stream | found | **found** (tests) | **found** (quality, tests) |
| R5 fileno() and pytest capture | missed | **found** (tests) | **found** (tests) |

Rung 2 had 2 of 6 for the right reason. Rung 3 has 3 with search and 4 without †. Several "found" real bugs come from the tests reviewer
saying "this new behaviour is untested"; whether that counts as finding the bug is exactly the round-2 question about restated bugs.

## 5 · Prediction vs result

| Predicted | Result |
|---|---|
| seeded recall, location 0.8 | 1.00 ✓ (better) |
| right-reason recall 0.6-0.8 | 1.00 † (better) |
| precision, location 0.5-0.7 | 0.46 ✗ (slightly worse) |
| 1-3 false alarms on clean PRs | 6 ✗ (worse) |
| with vs without search within ±1 bug, except S09 found only with search | ±1 bug ✓ (S10), but **S09 was found without search too** ✗, and precision differs far more than predicted |
| specialists stay in their areas, at least one exception | mostly ✓; the tests reviewer re-reports others' bugs widely |
| real 2-3 of 6 | 3 with search ✓, 4 without |
| at least one duplicate merged per PR on S01-S03 | only 2 merges in total ✗: specialists give the same bug different categories, so the exact-duplicate rule rarely fires (M7) |
| about 4× rung 2's tokens | about **10×** with search, 4× without ✗ |

## 6 · Incidents (all recorded, none hidden)

1. **Retrieval leaked across repos** (vector table, and in principle bm25). Found through cache misses, fixed mid-run, disclosed in the pre-registration with a correction.
2. **Three raw S01 answers from 29 Oct were overwritten** before the fix; their findings survive in `rung3_day1_partial.json`. Cached answers are now never overwritten.
3. **A stopped run overwrote the result file** once; fixed (`*_stopped.json`).
4. **R1/security failed once on a network error** on the laptop; re-asked later. R2 not sent (budget).
5. **The hand-check reader** would have dropped every other entry on blank files; fixed before your answers were read.
6. **The judge's first run had no API key** and reported "judged 27" while judging none; fixed, nothing was sent.

## 7 · Still to do

- [ ] Judge: last 6 verdicts (Gemini quota).
- [ ] Round 2: every hand-vs-judge disagreement plus the three flagged answers (M1 in both files, `HANDCHECK_RUNG3n.md` M8 and M22).
- [ ] Final numbers: remove the † marks; add the judge's numbers and its independent agreement rate.
