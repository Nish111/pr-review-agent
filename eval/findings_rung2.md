# Rung 2 results: one LLM reviewer

Run 24 Oct 2026 by Nishant after the pre-registration was committed (`eval/PREREG_RUNG2.md`).
Model `openai/gpt-oss-120b` on Groq, prompt sha `134aa0d267f5`. Raw answers: `eval/results/rung2_raw/`; scores: `eval/results/rung2.json`.

## 1 · Headline (seeded set, 14 PRs)

| | Rung 1 (rules) | **Rung 2 (one LLM)** |
|---|---|---|
| Precision, location match (pre-registered) | 0.22 | **0.70** (7/10) |
| Recall, location match (pre-registered) | 0.20 | **0.70** (7/10) |
| False alarms on the 4 clean PRs | 7 | **0** |
| **Recall, right reason** (Nishant's hand check, official) | 0.20* | **0.50** (5/10) |
| **Precision, right reason** | 0.22* | **0.50** (5/10) |

\* Rung 1 had no hand check; both of its matches (S01 rule S608, S06 rule DTZ011) name the planted bugs directly, so its right-reason numbers are taken as equal to its location numbers.

**What rung 2 found for the right reason:** S01 SQL injection, S02 timing attack, S03 path traversal, S04 partial write, S06 UTC vs local date.
**Located but judged a different problem:** S07 (reviewer flagged duplicate tags, not the missing test), S08 (see section 3).
**Missed:** S05 (N+1 queries), S09 (README now wrong: the README isn't in the PR, so the model never saw it), S10 (see section 4).

## 2 · Real click PRs (per PR, no percentage)

| PR | Result | Note |
|---|---|---|
| R1 | missed | — |
| R2 | **not reviewed** | 193 changed lines don't fit the 5,000-token budget even at ±10 lines; correctly not sent (S1 rule) |
| R3 | **found, right reason** | "Fish completion splits on literal `\n` instead of a real newline" |
| R4 | **found, right reason** | "`__next__` raises EOFError instead of StopIteration": the regression click later fixed |
| R5 | missed | Windows/pytest-internal behaviour; not visible from the diff |

**Prediction "0–2 of 6": held (2 of 6).** Click's own reviewers merged both R3 and R4; rung 2 would have flagged them.

## 3 · The right-reason check: you vs the AI judge

| | Round 1 (independent) | Round 2 (after seeing the 3 disagreements) |
|---|---|---|
| You: right reason | 7 / 9 | **6 / 9 (official)**: changed M6→no, M9→yes, kept M7 no |
| Judge (gemini-3.6-flash): right reason | 8 / 9 | 8 / 9 |
| Agreement | **6 / 9** | 8 / 9 (only M7, S08, still differs) |

- **Round 1 is the honest measure of the judge:** an independent agreement of 6/9 (67%) is **not good enough to replace the hand check** on rungs 3–4. Round 2's agreement is inflated by design (you'd seen the judge).
- **M9 was the label's fault, not the judge's or yours:** R4's label carried only click's commit title. Fix, pre-registered before rung 3: every real label gets the plain-words description from `REAL_PRS_REVIEW.md`.
- **M7 (S08) stays "no" by your call.** The judge and Claude read it as the same bug ("the test no longer verifies results"). Recorded as a disagreement, not overridden.

## 4 · Findings that matched no label (pre-registered: checked before being called false alarms)

| PR | Finding | Claude's verdict | Why |
|---|---|---|---|
| S09 | "json.dumps tries to convert sqlite3.Row objects" | **false alarm** | the code does `dict(r)` first, which works for sqlite3.Row |
| S10 | "CLI help text mentions only .txt despite the new json format" (cli.py:12) | **real**: the planted docs problem, **4 lines away** from the label | right reason, wrong place: the ±3 rule misses it (the reverse of rung 1's R2 coincidence) |
| S10 | "Docstring says output is always .txt" (export.py:13) | **real, not planted** | the PR added `fmt` but left the docstring saying `.txt` |

*(Claude's verdicts with reasons; correct any you disagree with.)* Counting real problems instead of label matches, rung 2 raised **7 useful findings out of 10** (5 right-reason + 2 real docs issues), with 1 false alarm and 2 located-but-wrong-reason.

## 5 · Incidents and instrument problems (all recorded, none hidden)

1. **Our parser lost a correct answer (S01).** The answer was valid JSON, but its suggestion contained a ```python fence, and our extractor cut on it.
   Fixed with a regression test; re-scored from the saved answers, no model re-ask. As-run numbers (`rung2_as_run.json`): precision 0.67 (6/9), recall 0.60.
   **Official = corrected**, because the pre-registration specified strict JSON parsing and the answer *was* valid JSON.
2. **The location rule cuts both ways:** it credited a wrong reason in rung 1 (R2), and here it missed a right reason 4 lines off (S10). The right-reason check is now essential, not optional.
3. **The context budget blocks real PRs:** R2 can't be reviewed in one call. That's the motivation for rung 3 (retrieval picks the relevant slices, and specialists split the work).
4. **Speed and cost:** 18 calls, 624–3,315 tokens each, 1–37 s each, zero cost, no quota errors on Groq. The judge needed 2 transport retries on Gemini (503s).

## 6 · Prediction vs result

| Predicted | Result |
|---|---|
| seeded recall 0.5–0.7 | 0.70 location / 0.50 right-reason ✓ |
| precision 0.3–0.6, false alarms on C03/C04 | 0.70 / 0.50; **zero** false alarms on clean PRs ✗ (better than predicted) |
| S09 missed | ✓ |
| real 0–2 of 6 | 2 ✓ |
