# S6 — Default configuration: four specialists, no code search, calibrated threshold 0.84

- **Date:** 2026-11-07
- **Status:** accepted (Nishant, `eval/findings_rung4.md` decision D = A)
- **Phase / milestone:** 19 HITL · M7

## Context
Rung 3 (`eval/findings_rung3.md`) ran the four specialists with and without code search. Rung 4 (`eval/findings_rung4.md`)
calibrated a posting threshold on the hand-checked golden set, judged by leave-one-PR-out against the G0 target of 90% precision.
- With search: no threshold reaches 90% (10 of 12 folds had none; the 2 comments it did post were wrong). Everything would go to the queue.
- Without search: 8 of 8 posted comments right under leave-one-PR-out (95% range 0.68-1.00); in-sample threshold 0.84 posts 10, all right.

## Decision
The reviewer runs the four specialists **without** code search, and posts a comment by itself only if its calibrated score is
**≥ 0.84**. Everything else goes to the approval queue; critical findings and partial reviews always go to a human (M1 `route()`).
The calibration table is `eval/results/rung4n.json`. Code search (M5) stays in the code, off by default (`search=False` in `src/pr_review/config.py`).

## Consequences
- Positive: the only configuration that met the precision target honestly; fewer comments; about 4× rung 2's tokens instead of 10×.
- Negative / cost: the evidence is small (8 posted comments under the fair test; 14 PRs), and the without-search labels had one fewer
  check than the with-search ones. Disputes (M7 queue) become new labels, so the threshold must be recalibrated as they accumulate.
- Search's one extra planted find (S10) is given up. It can come back if a later rung filters the docs reviewer's comments, which needs a new pre-registration.

## Alternatives rejected
- B · with search, as pre-registered: honest, but nothing ever posts; every comment waits for a human.
- C · with search minus "docs reviewer alone": a rule chosen after seeing the data; would need a new pre-registration and fresh PRs.
