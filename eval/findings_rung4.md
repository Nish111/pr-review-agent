# Rung 4 results: aggregator + calibrated threshold + approval queue

Run 7 Nov 2026 by Nishant after `eval/PREREG_RUNG4.md` was final. **No model calls**: rung 4 re-reads rung 3's saved findings.
Results: `eval/results/rung4.json` (on rung 3 with search, official) and `rung4n.json` (on rung 3 without search).
Labels: your final hand check (round 2; round 2b pairs left open) + the unmatched-finding verdicts you sample-checked (9/10 agreed).

## 1 · Headline

| | **On rung 3 with search (official)** | On rung 3 without search |
|---|---|---|
| Comments before → after grouping (seeded) | 50 → **33** | 29 → 17 |
| **A · leave one PR out (official)** | **no threshold in 10 of 12 PRs**; in the other 2 it posted 2 comments, **both wrong** (precision 0.00) | a threshold in every PR; posted **8, all right** (precision 1.00; 95% range 0.68-1.00, because 8 is a small number) |
| B · in-sample (optimistic) | **no threshold** | threshold 0.84: posts 10 comments, all right |
| C · real click PRs (seeded threshold applied) | nothing posts (no threshold) | nothing posts: real comments score 0.76, below 0.84, although 5 of 7 are right |
| **Outcome** | **`threshold = None`: every comment goes to the approval queue** | the bot may post comments scoring ≥ 0.84; everything else goes to the queue |

**In one sentence:** with code search, nothing the reviewers say can be trusted to post on its own; without search, a calibrated
threshold posts about half of the comments, and every one it posted was right, on 14 PRs, a small sample.

## 2 · What the calibration learned (table from `rung4.json` and `rung4n.json`)

| Kind of comment (lead specialist / kind / agreement) | with search: right of total | without search: right of total |
|---|---|---|
| docs, test/doc kind, alone | **2 of 19** | 3 of 6 |
| security, bug, ≥2 specialists agree | 4 of 5 | **5 of 5** |
| quality, bug, ≥2 agree | 3 of 4 | 2 of 2 |
| quality, bug, alone | 0 of 1 | 1 of 2 |
| tests, test/doc kind | 0 of 1 | 2 of 2 |

As predicted, "a bug comment two reviewers agree on" ranks highest and "the docs reviewer alone" lowest. With search, the docs
reviewer alone wrote **19 of the 33** grouped comments and was right twice. That one row is why search fails rung 4.

## 3 · Why the same reviewers pass without search and fail with it

- **Volume:** search gives the docs reviewer the README, changelog and other files, and it comments on all of them (§2).
  Those comments drag the overall right-rate down, so no score clears 0.90 on enough comments.
- **Leave-one-PR-out exposed it:** in the 2 PRs where a threshold could be chosen, the comment it posted was wrong (S07, S09).
  An in-sample number would never show that.
- **Caution:** the without-search labels had one fewer check (no AI judge, round 2 only for 3 items), and round 2b left five
  inconsistent pairs. Its 8 of 8 may be a little flattering; it is still clearly better than with search on every measure here.

## 4 · What gets posted, without search, at the demo threshold (0.84)

10 comments on the 10 planted PRs, all labelled right: security on S01, S02, S03, S07 and S09; quality on S04, S05 and S06; tests
on S08 and S10. 9 of the 10 planted bugs are covered (S10's posted comment is a real but unplanted problem: the new JSON export has no
test). Nothing posts on the clean PRs. The approval queue gets the remaining 7 comments.

## 5 · Prediction vs result

| Predicted (PREREG_RUNG4) | Result |
|---|---|
| grouping cuts comments by about a third with search | 50 → 33 (34%) ✓ |
| no threshold reaches 0.90 under leave-one-PR-out with search | ✓ (and the 2 comments it did post were wrong) |
| without search, a threshold may just reach 0.90, posting a minority | ✓ reached (8/8), posting 8 of 17 (about half) |
| "bug, ≥2 agree" ranks highest, "docs alone" lowest | ✓ |
| queue for a typical seeded PR holds 2-4 comments | with search: 2.4 per PR (all comments) ✓; without: about 0.5 per PR |

## 6 · The decision this creates

See ★ below. It decides what the live demo (M9) runs.

## ★ D · What should the reviewer run by default?

| | What happens |
|---|---|
| **A · without search, calibrated threshold 0.84 (recommended)** | The only configuration that met the 90% target honestly (leave-one-PR-out). The bot posts the comments it is calibrated to trust and queues the rest. Code search stays in the code, switched off by default. Its single extra find (S10) doesn't pay for its noise on this data. Risk: 8 of 8 is a small sample; the dispute path (M7) collects the evidence to recalibrate. |
| **B · with search, as pre-registered (official rung 3)** | Faithful to the official arm, but with `threshold = None` nothing ever posts by itself: every comment waits for a human. The demo then shows the approval queue, not the bot posting. |
| **C · with search, but drop "docs reviewer alone" comments before calibrating** | Might rescue search, but it's a new rule chosen after seeing the data: it would need a new pre-registration and a fresh golden set to test honestly. |
| **If you don't decide** | A, written up as "chosen from rung 4's results", with B's outcome reported next to it. |

**Your answer (Nishant, 7 Nov 2026):** A. The default is rung 3 **without** code search, with the calibrated threshold 0.84 (chosen on all 14 seeded PRs, `rung4n.json`). Code search stays in the code, switched off. Recorded as decision S6 (`.genesis/decisions/S6-default-configuration.md`).
