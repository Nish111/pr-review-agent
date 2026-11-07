# Rung 3 results: four specialists, with and without code search

Final, 7 Nov 2026: right-reason numbers use your **round 2** answers (official). Round 1 and the AI judge are reported alongside.
Runs: 29-31 Oct 2026, model `openai/gpt-oss-120b` on Groq, prompts as pre-registered (`eval/PREREG_RUNG3.md`).
Raw answers: `eval/results/rung3_raw/`; scores: `eval/results/rung3.json` (with search, official) and `rung3n.json` (without).
Two retrieval bugs were found and fixed mid-run (see the pre-registration's last section); no official answer used leaked context.

> **One open item (round 2b):** five comments appear in both runs with opposite answers (pairs listed at the end of
> `eval/HANDCHECK_RUNG3_ROUND2.md`). They were left unanswered, so as announced the numbers below keep both answers and are
> marked ‡ where a pair affects them. The biggest effect is on the real-PR comparison (§4).

## 1 · Headline (seeded set, 14 PRs)

| | Rung 2 (one LLM) | **Rung 3, with search (official)** | Rung 3, without search |
|---|---|---|---|
| Findings | 10 | **50** | 29 |
| Recall, location | 0.70 | **1.00** (10/10) | 0.90 (9/10; S10 missed) |
| Precision, location | 0.70 | **0.46** (23/50) | 0.66 (19/29) |
| False alarms on the 4 clean PRs | 0 | **6** | 2 |
| **Recall, right reason** (your hand check, round 2) | 0.50 | **1.00** (10/10) | 0.90 ‡ (9/10) |
| **Precision, right reason** | 0.50 | **0.30** ‡ (15/50) | 0.55 ‡ (16/29) |
| Real click PRs, right reason (of 6 bugs) | 2 | **0** | 4 ‡ |
| Estimated prompt tokens, seeded set | ~16,000 | ~171,000 | ~69,000 |

Round 1 for comparison (with search): right-reason precision 0.36, real PRs 3. The AI judge (with search): precision 0.28, recall 10/10, real PRs 0.

**In one sentence:** rung 3 finds every planted bug for the right reason, but two in three of its comments with search are noise, and on the real click PRs it found nothing for the right reason.

## 2 · What each change did

- **Splitting into specialists (rung 2 → rung 3 without search):** right-reason recall 0.50 → 0.90, precision 0.50 → 0.55,
  false alarms on clean PRs 0 → 2. It found S05 (N+1 queries), S07 (missing test), S08 (weakened test) and S09, which rung 2 missed.
  **This is the change that earned its place.**
- **Adding code search (without → with):** +1 planted bug (S10), but +21 comments, 4 more false alarms on clean PRs, right-reason
  precision 0.55 → 0.30, and real PRs 4 → 0 ‡. Most of the extra comments are the **docs reviewer** (12 → 26): with the README and other files
  in view, it flags "not documented" everywhere, including on clean PRs.
- **For the vector lane (matrix 03, R5) and search in general:** on this golden set, search buys one bug for a large precision cost.
  It doesn't earn its place as is. The response is rung 4 (aggregator and calibration), which can down-weight exactly these comments.

## 3 · Which specialist found what (right reason, round 2)

| Bug | with search | without search |
|---|---|---|
| S01 SQL injection | security, tests, docs ‡ | security, tests |
| S02 timing attack | security, tests | security, quality |
| S03 path traversal | security | security, quality |
| S04 partial write | quality ‡ | quality |
| S05 N+1 queries | quality | quality, docs |
| S06 UTC vs local date | quality | quality |
| S07 missing test | tests ‡ | quality, security |
| S08 weakened test | quality, tests | quality, tests |
| S09 README now wrong | docs, quality ‡ | docs, tests ‡ |
| S10 CLI help now wrong | docs | — |

The planned split held: security found S01-S03, quality S04-S06, tests S07-S08, docs S09-S10.

## 4 · Real click PRs (per PR, no percentage; right reason, round 2)

| PR | Rung 2 | Rung 3 with search | Rung 3 without search |
|---|---|---|---|
| R1 colour codes in prompts | missed | missed (only "this isn't tested", judged not the bug) | found (quality, tests) |
| R2 pager temp file | not sent | not sent (too large, as pre-registered) | not sent |
| R3 fish completion | found | missed (docs comment judged not the bug) | found (quality, tests) |
| R4 EOFError on the stream | found | missed ‡ ("EOFError isn't tested", judged no) | found ‡ (incl. "iterating over the stream now raises EOFError", the bug itself) |
| R5 fileno() and pytest capture | missed | missed ("fileno() isn't tested", judged no) | found (tests: "tests expecting fileno() to raise now get -1") |

**Caution on the 0-vs-4 gap:** the with-search run had two extra checks (the AI judge and round 2), and its "not tested" comments
were turned to `no` there; the without-search run's real-PR answers were only checked once. Part of the gap is that asymmetry, not the
reviewers. The one clear case is R4: without search, the quality reviewer named the bug itself; with search, no reviewer did.

## 5 · The AI judge (with-search run)

- **Independent agreement with your round 1: 18 of 27 (67%)**, the same rate as rung 2 (6 of 9). After round 2: 26 of 27.
- The judge was stricter than your round 1 on "not tested" comments, and in round 2 you changed 8 of the 9 disagreements to its answer (M19 kept).
- **Decision stays:** an AI judge at 67% independent agreement isn't good enough to replace the hand check; the hand check stays official for rung 4.

## 6 · Prediction vs result

| Predicted | Result |
|---|---|
| seeded recall, location 0.8 | 1.00 ✓ (better) |
| right-reason recall 0.6-0.8 | 1.00 ✓ (better) |
| precision, location 0.5-0.7 | 0.46 ✗ (slightly worse) |
| 1-3 false alarms on clean PRs | 6 ✗ (worse) |
| with vs without search within ±1 bug, S09 only with search | ±1 bug ✓ (S10), but S09 was found without search too ✗, and precision differs far more than predicted |
| specialists stay in their areas, at least one exception | ✓ |
| real 2-3 of 6 | **0** with search ✗, 4 without |
| at least one duplicate merged per PR on S01-S03 | only 2 merges in total ✗: specialists give the same bug different categories (fixed by rung 4 grouping) |
| about 4× rung 2's tokens | about **10×** with search, 4× without ✗ |

## 7 · Incidents (all recorded, none hidden)

1. **Retrieval leaked across repos** (vector table, and in principle bm25). Found through cache misses, fixed mid-run, disclosed in the pre-registration with a correction.
2. **Three raw S01 answers from 29 Oct were overwritten** before the fix; their findings survive in `rung3_day1_partial.json`. Cached answers are now never overwritten.
3. **A stopped run overwrote the result file** once; fixed (`*_stopped.json`).
4. **R1/security failed once on a network error** on the laptop; re-asked later. R2 not sent (budget).
5. **The hand-check reader** would have dropped every other entry on blank files; fixed before your answers were read.
6. **The judge's first run had no API key** and reported "judged 27" while judging none; fixed, nothing was sent.

8. **Round 2 found inconsistent answers** across the two runs (round 2b, five pairs); left open, so marked ‡ above.

## 8 · What this means for rung 4

Rung 4 (no new model calls) must turn 50 noisy comments into a few trustworthy ones. The data says where to start: the docs
reviewer alone, and "not tested / not documented" comments, are rarely right; bug comments that two reviewers agree on usually are.
Pre-registered in `eval/PREREG_RUNG4.md`; prediction: no threshold reaches 90% precision with search under leave-one-PR-out.
