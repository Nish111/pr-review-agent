# Pre-registration: rung 4 (aggregator + calibrated confidence + approval queue)

**Final, 7 Nov 2026** (drafted 1 Nov). Committed before rung 4 is run on the golden set. It learns from rung 3's final labels:
round 2 hand-check answers (round 2b pairs were left open, so both answers stand) and the sample-checked unmatched verdicts.

> **What you need to do in this file:** two decisions, marked ★ (D1 and D2). Write your answer under each. You can answer
> now; nothing runs until round 2 is finished.

## What rung 4 is (plain words)

Rung 4 adds **no new model calls**. It takes rung 3's findings, which are already saved, and adds the editor described in
`FAILURE_MATRIX_05_AGGREGATION.md`:
1. it groups comments on the same lines into one, whatever their category (G1);
2. it turns "and no test/doc covers it" restatements into supporting lines under the real comment (G2);
3. it gives each remaining comment a **calibrated score**: how often comments like it were right on the golden set (G4);
4. it posts a comment only if that score clears a threshold that reaches **≥ 90% precision** (the G0 target), and sends the rest to the approval queue.

Because there are no model calls, rung 4 costs no quota, and it runs on **both** rung 3 arms (with and without search).

## Fixed choices

| Choice | Value | Where it comes from |
|---|---|---|
| Input | rung 3's saved findings: `rung3.json` (official) and `rung3n.json` | no new calls |
| Truth for "right" | your final (round 2) right-reason answers for matched findings, plus D2 for unmatched ones | rung 3 hand check |
| Grouping | same file, overlapping lines (±3, the scoring tolerance), any category | matrix 05, G1 |
| Kinds | a comment is **test/doc kind** if its category or summary is about tests or documentation (missing test, coverage, docstring, README, help text); otherwise **bug kind**. In a group, the posted **lead** is the most confident bug-kind comment; test/doc comments become supporting lines, and lead only when the group has nothing else | matrix 05, G2; rule in `aggregator/aggregate.py` |
| What counts as right for a group | the group is right if its **lead** is right (the lead is the text that gets posted) | the posted comment is what a developer reads |
| Score features (few, because 14 PRs is little data) | the lead's specialist; bug vs test/doc kind; how many specialists are in the group (1 or ≥2); model confidence band (<0.8, ≥0.8) | matrix 05, G3-G4 |
| Score | observed right-rate of comments with the same features, smoothed toward the overall rate so a group of 1-2 comments can't score 100% | standard small-sample practice (add-one smoothing) |
| Target | precision ≥ 0.90 on posted comments | G0 DONE.html §1 |
| Outcome if no threshold reaches the target | `threshold = None`: everything goes to the approval queue, and that is the reported result | invariant `bot_never_approves_or_merges` |

## ★ D1 · How is the threshold chosen and tested?

| | What happens |
|---|---|
| **A · leave one PR out (recommended)** | For each of the 14 seeded PRs: choose the threshold on the other 13, apply it to this one. The reported precision is what a **new** PR would see, which is honest with so little data. The final threshold for the demo is then chosen on all 14. Expect a lower, wider-ranging number than B. |
| **B · choose and test on all 14 together** | Simpler, and the number looks better, but it is the number for PRs the threshold has already seen. A reviewer of your work will discount it, and they'd be right to. |
| **C · choose on the seeded PRs, test on the 5 real click PRs** | Tests on genuinely unseen code, but 5 PRs and 6 bugs is too few to say anything about 90%. Reported per PR, as decision A on the real set says. Can be added on top of A. |
| **If you don't decide** | A, with C reported alongside as an extra, per-PR view. |

**Your answer (Nishant, 1 Nov 2026):** A, B and C, all three reported.
- **Official:** A (leave one PR out). The 0.90 target is judged on this number only.
- **Also reported, labelled as optimistic:** B (chosen and tested on all 14), so the gap between A and B shows how much the small data flatters an in-sample number.
- **Also reported, per PR:** C (threshold chosen on the 14 seeded PRs, applied to the 4 reviewed click PRs; R2 has no findings).

## ★ D2 · What about findings that match no known bug?

Calibration needs every finding marked right or wrong, not just the ones that landed on a known bug. With search, rung 3
has 27 unmatched findings (21 on PRs with planted bugs, 6 on clean PRs); without search, 10. In rung 2, two unmatched
findings turned out to be **real** docs problems, so "unmatched" doesn't always mean "wrong".

| | What happens |
|---|---|
| **A · Claude reviews each unmatched finding, you check a sample (recommended)** | Claude writes a verdict with a one-line reason for each, in a file like the hand-check files. You check a random 10 and say whether you agree. If you disagree with 3 or more of the 10, you check all of them. About 15 minutes of your time; the labels are close to honest. Risk: Claude marking its own model's work; the sample check is there to catch that. |
| **B · you check all of them** | The most trustworthy, about 30-40 minutes for both arms. |
| **C · every unmatched finding counts as wrong** | No work, and it's conservative: the threshold comes out stricter, so fewer comments post. But it punishes real-but-unplanted findings (rung 2's two docs issues would count as errors). |
| **If you don't decide** | A. |

**Your answer (Nishant, 1 Nov 2026):** A. Claude labels each unmatched finding with a one-line reason; Nishant checks a random 10
(drawn by a fixed seed, so the sample is reproducible); 3 or more disagreements → he checks them all.

## Prediction (written before running)

- Grouping cuts comments per PR by about a third with search (rung 3: 50 comments for 14 PRs), mostly by folding the tests and docs restatements.
- **No threshold reaches 0.90 under leave-one-PR-out with search**; the official outcome is likely "everything to the queue", with a
  best posted precision around 0.6-0.8. Without search, a threshold may just reach 0.90, posting a minority of comments.
- The calibration will rank "primary comment, ≥2 specialists agree" highest and "docs reviewer, alone" lowest.
- The approval queue for a typical seeded PR holds 2-4 comments after grouping.

## How to run (only after round 2 is final and this file is committed)

No API keys needed; no model calls.
1. `PYTHONPATH=src python -m pr_review rung4 --on 3` (official, rung 3 with search) → `eval/results/rung4.json`
2. `PYTHONPATH=src python -m pr_review rung4 --on 3n` (rung 3 without search) → `eval/results/rung4n.json`

Labels it reads: the hand-check files (final round) and `eval/UNMATCHED_RUNG3.md` / `UNMATCHED_RUNG3n.md` (Claude's verdicts, after
your sample check in `eval/UNMATCHED_SAMPLE_CHECK.md`). It refuses to run while any posted comment has no label.
