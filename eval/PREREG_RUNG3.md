# Pre-registration: rung 3 (four specialists with code search)

Written 27 Oct 2026, **before** rung 3 is run. Commit this first, run after. Same discipline as `PREREG_RUNG1.md` and `PREREG_RUNG2.md`.

> **What you need to do in this file:** two decisions, marked ★ (D1 and D2). Write your answer under each.
> Everything else is fixed and derived from earlier decisions; push back if anything looks wrong.

## What rung 3 is (plain words)

Instead of one reviewer, four narrower ones (security, quality, tests, docs) each review the PR with their own
instructions, and each also sees related code from the rest of the repository, found by M5's search. Their findings
are put together, with exact duplicates removed (the full merge is rung 4). See `FAILURE_MATRIX_04_SPECIALISTS.md`.

Rung 3 changes **two** things at once compared with rung 2: the split into specialists, and the code search. To tell
which one helped, decision D1 proposes running rung 3 twice: with search and without.

## Fixed choices (none may change after the first run without a new pre-registration)

| Choice | Value | Where it comes from |
|---|---|---|
| Model | `openai/gpt-oss-120b` on Groq, temperature 0 | same as rung 2, so the rungs differ in design, not model (S1: one named model per rung) |
| Prompts | `prompts/rung3_security.txt` sha `97f82a1e3926`, `rung3_quality.txt` sha `6182838ac2bb`, `rung3_tests.txt` sha `193fad60fc04`, `rung3_docs.txt` sha `d48d1966c39b` | written by Claude from the brief's four areas; not tuned on any golden PR |
| Changed-file context | as rung 2: diff + whole changed files, trimmed to ±30 then ±10 lines if over budget | rung 2 pre-registration |
| Related code | M5 search for the PR, at most **1,500 tokens**, from the index at the PR's **base** commit; chunks of files the PR changes are left out (matrix 04, W6) | matrix 03 R6, R7 |
| Index | seeded PRs: `golden/seeded/base`; real PRs: click at the parent of each PR's commit; model bge-small (S2, version recorded in the index) | S2 amended 26 Oct |
| Budget | each call ≤ 5,000 tokens; all four share one 8,000 tokens-per-minute budget (matrix 04, W2) | S1 |
| Calls | one per specialist per PR; a dropped connection is retried, a bad answer is not | rung 2 rule |
| Output handling | strict parse; ungrounded findings dropped and logged; evidence must be in the shown changed lines or a shown related chunk | invariant `every_posted_finding_is_grounded` |
| Merge | exact duplicates only: same file, overlapping lines, same category; higher confidence kept | matrix 04, W5 |
| Scoring | as rungs 1-2: same file, lines within ±3; precision on all 14 seeded, recall on the 10 planted; real set per PR (decision A) | `GOLDEN_SET_PLAN.md` |
| Right reason | your hand check is official, the Gemini judge (`gemini-3.6-flash`, prompt sha `971537b18244`) is reported alongside with the agreement rate | rung 2 decision (A and B) |
| Real labels | each now carries a plain-words description (`plain` in `golden/labels_real.json`), taken from `REAL_PRS_REVIEW.md` v2, which you reviewed on 24 Oct | rung 2 lesson (`findings_rung2.md` §3) |

## ★ D1 · Run rung 3 once or twice?

| | What happens |
|---|---|
| **A · twice: with search (official) and without (recommended)** | We can say *which* change helped: specialists alone (rung 3 without search vs rung 2), and search on top (with vs without). That is the evidence matrix 03 says decides whether the vector lane earns its place (R5). Cost: about **550,000 tokens**, roughly **3 days** of one Groq model's free daily quota. The run stops cleanly when a day's quota is spent and continues from the cache next time. |
| **B · once, with search only** | About 275,000 tokens, roughly 1.5 days. But the result mixes two changes, so if rung 3 beats rung 2 we can't say whether it was the specialists or the search, and the "does search help?" question in matrix 03 stays unanswered. |
| **If you don't decide** | A. |

**Your answer:** A

## ★ D2 · Hand-check one run or both?

Every finding that lands on a labelled bug gets the right-reason check, as in rung 2 (expected ~15-25 per run).

| | What happens |
|---|---|
| **A · both runs (recommended, if D1 = A)** | The with/without comparison is in right-reason numbers, the honest ones (rung 2 showed location-only can be off in both directions). Your time: roughly 25-35 minutes, in two files (`eval/HANDCHECK_RUNG3.md` and `eval/HANDCHECK_RUNG3n.md`). |
| **B · the official run only** | Half the time. The with/without comparison is then in location-only numbers, with that weakness stated in the write-up. |
| **If you don't decide** | A if D1 = A; otherwise there's only one run. |

The Gemini judge has 20 requests a day, so it runs on the official (with-search) run only, possibly over 2 days.

**Your answer:** A

## Prediction (written before running, so it can be wrong in public)

- **Seeded recall, location:** 0.8 (8 of 10), with search. New compared with rung 2: **S07** (the tests reviewer notices the missing test), **S10** (the docs reviewer), and **S09** (the README that is now wrong; only search can show it, because the README isn't in the PR). Still likely missed: S05 (N+1 queries) or S08.
- **Seeded recall, right reason:** 0.6–0.8.
- **Seeded precision, location:** 0.5–0.7, lower than rung 2's 0.70, because four reviewers each look harder and some real-but-unplanted problems (like rung 2's extra S10 docstring) count as unmatched.
- **False alarms on the 4 clean PRs:** 1–3 (rung 2 had 0).
- **With vs without search:** the same within ±1 bug, **except S09**, found only with search.
- **Which specialist finds what:** security S01–S03, quality S04–S06, tests S07–S08, docs S09–S10; at least one bug found by a specialist outside its area.
- **Real click PRs:** 2–3 of 6 (R3 and R4 again; R1 possibly via the quality reviewer). **R2 still not reviewed**: its 193 changed lines don't fit 5,000 tokens.
- **Duplicates removed:** at least one per PR on S01–S03, where security and quality overlap.
- **Tokens:** about 4× rung 2 per PR, plus the related code. That cost is the price of the split, reported next to whatever it gains.

## How to run (after this file is committed)

Needs `GROQ_API_KEY` and `GEMINI_API_KEY` in the environment, as for rung 2, and the click clone at `../../click`.
The first run also extracts each real PR's **base** version of click into `eval/workdir/` (the program runs
`git archive` in the click clone, as rung 2 did for the head versions) and builds the code index there (`eval/workdir/rung3_index.db`).

1. With search (official): `PYTHONPATH=src python -m pr_review eval --rung 3 --arm search --provider groq --model openai/gpt-oss-120b --click ../../click`
2. Without search (only if D1 = A): the same command with `--arm nosearch`.
   If either prints `STOPPED: daily quota exhausted`, run the same command again after the quota resets. Answers already received are reused, never re-asked.
3. Judge (official run only): `PYTHONPATH=src python -m pr_review rightreason judge --rung 3 --provider gemini --model gemini-3.6-flash`. Gemini allows 20 requests a day; if it stops, run it again after the reset.
4. Hand check: `PYTHONPATH=src python -m pr_review rightreason handcheck --rung 3` (and `--rung 3n` if D2 = A), then fill in the file(s) **before** step 5.
5. Compare: `PYTHONPATH=src python -m pr_review rightreason compare --rung 3`.

## Changed before any rung 3 call (recorded so nothing is hidden)

- 27 Oct: retrieval for a diff now ignores plain English words from comments and docstrings in the changed lines
  (only code-like names or names defined in the repo are searched), the same rule the free-text search got after the
  M5 demo. Checked on the seeded set only for "does the README still come back for S09" (it does); no reviewer was run.

## Changed after the first calls (30 Oct 2026; recorded so nothing is hidden)

- **Bug found: the vector search could see other repositories.** The vector table had no repo column; the search took
  the 90 nearest chunks across *all* indexed repos and then kept only the PR's repo. Once click was indexed (for the real
  PRs), notes-svc's nearest chunks could be crowded out, so retrieval for a seeded PR changed. It showed up as a cache miss:
  on 30 Oct the with-search run tried to re-ask S01 instead of reusing its answer.
- **Effect on answers already received:** none for the seeded PRs. All 14 were asked on 29-30 Oct **before** click was
  indexed, when notes-svc was the only repo, so their related code was exactly what the pre-registered design intended. The real
  PRs were asked with notes-svc's ~30 chunks also in the table; any real PR whose related code changes under the fix is re-asked
  (the cache key includes the full prompt), so every official answer matches the fixed design.
- **Fix:** the vector table is now partitioned by repo (`chunks_vec_repo`), filled from the saved vectors without re-embedding.
  Tests: a second repo no longer changes the first repo's results; an old index is filled without new embeddings.
- **Second fix:** a run that stops on the quota no longer overwrites a more complete result file. It saves to
  `rung3_stopped.json` instead. (On 30 Oct the stopped run replaced `rung3.json` with an empty result; the answers were
  never lost, because they are cached, and re-running regenerates the file.)

