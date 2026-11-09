# Failure matrix 07 · Evaluation & learning

Draft v1, 9 Nov 2026, the last of the seven groups. Same loop as matrices 01-06. The brief's group 7: *golden PRs → precision/recall
of baseline vs upgraded; a regression gate blocks a worse prompt.* The **baseline** is `pr-review-agent.html`: a golden dataset,
an LLM-as-judge and a regression gate.

> **What you need to do in this file:** nothing to answer. Most of these failures **actually happened** during M2-M9, and the card says where.

---

## What this component is (read this first)

Everything we claimed (rung 3 finds every planted bug, rung 4 posts 8 of 8 correctly) is only as good as the way it was measured.
This component is the measuring: the golden set, the labels, the scoring, the pre-registrations, the judge, the hand checks. It also
keeps the system from getting worse over time (a regression gate) and lets it learn from people's verdicts (disputes become labels).

## 1 · Purpose and contract

- **In:** a candidate change (a new prompt, model or rule), the golden set, the committed baseline results.
- **Out:** the rung's numbers (location and right-reason), a pass/fail from the regression gate, and a recalibration report from human verdicts.
- **Invariant:** a number is official only if its pre-registration was committed before the run; anything changed afterwards is listed in that pre-registration.

## 2 · Failure modes (✓ = seen in this project)

**L1 · Tuning on the data you test on.** ✓ (M5: exact-name search tuned after looking; rung 4 threshold)
- **What we built:** pre-registrations before each run; leave-one-PR-out for the threshold; post-hoc numbers labelled as such (`FAILURE_MATRIX_03` §5).

**L2 · Location matches credit the wrong reason, or miss the right one.** ✓ (rung 1 R2 coincidence; rung 2 S10 four lines off)
- **What we built:** the right-reason check on every location match; the official number is the hand check.

**L3 · The AI judge isn't reliable enough to replace a person.** ✓ (independent agreement 6/9 in rung 2, 18/27 in rung 3)
- **What we built:** the judge reports alongside the hand check, never instead of it; its verdicts are hidden until the hand check is done.

**L4 · Labels are inconsistent.** ✓ (round 2b: five identical comments with opposite answers across the two runs)
- **What we built:** a consistency pass that finds identical comments with different answers; unresolved pairs are marked ‡ in the write-up.

**L5 · The instrument breaks, not the system.** ✓ (rung 2 parser lost a correct answer; rung 3 cache misses from leaked retrieval; the hand-check reader skipped every other blank entry)
- **What we built:** each bug fixed with a test; the as-run numbers kept next to the corrected ones; cache keyed on the full prompt; superseded answers kept.

**L6 · A change quietly makes reviews worse.** *(not yet seen; the brief's regression gate)*
- **What we build:** `python -m pr_review gate`: compares a candidate run with the committed baseline on the seeded set. It **fails** if
  location recall drops, if location precision drops by more than 0.05, or if there are more false alarms on clean PRs. Matched findings
  whose right-reason label isn't known yet (new wording) make the result **"needs hand check"**, never "pass".

**L7 · Learning from humans goes wrong.** *(new in M9)*
- **What goes wrong:** approvals, rejections and disputes in the queue are the system's only new labels after the golden set. One person
  rejecting everything, or a burst of disputes on one PR, could swing the calibration.
- **What we build:** `python -m pr_review recalibrate` **reports**, it doesn't apply: golden-set labels plus queue verdicts, with counts
  per source, and the leave-one-PR-out result. Changing the live threshold stays a human decision recorded like S6.

**L8 · The golden set is too small.** ✓ (14 seeded PRs, 5 real; 8 posted comments behind "8 of 8")
- **What we built:** every rate is shown with its counts; rung 4 shows a 95% range. New real labels come from the queue (L7).

**L9 · Same prompt, different answers.** *(known, not measured)*
- **What goes wrong:** temperature 0 isn't fully deterministic on hosted models. S1 planned 3 repeat runs on a 5-PR subset; quota went to the two rung 3 arms instead.
- **Status:** **not measured**; stated as a limitation in the write-up.

**L10 · Gaming precision by saying less.** *(design risk)*
- **What goes wrong:** posting fewer comments raises precision for free.
- **What we built:** precision is always reported with recall and the number of comments posted (rung 4 tables).

## 3 · Tests

| Test | Failure | Pass means |
|---|---|---|
| Q1 | L6 | a candidate with lower recall fails the gate |
| Q2 | L6 | an identical candidate passes |
| Q3 | L6 | a candidate with a new, unlabelled matched finding returns "needs hand check" |
| Q4 | L7 | queue verdicts appear in the recalibration report with their source, and nothing changes the live threshold |

## 4 · Glossary

| Term | Meaning |
|---|---|
| **Golden set** | the PRs with known answers we score against: 14 seeded + 5 real |
| **Regression gate** | an automatic check that a change didn't make the numbers worse |
| **Recalibration** | recomputing the calibrated scores and threshold from new labels |
| **Pre-registration** | writing down the method and predictions, committed, before running |
