# S4 — Golden PR set: seeded PRs + real issue-linked PRs

- **Date:** 2026-10-21
- **Status:** accepted (decided by Nishant, `M0_SPIKES.md` → S4, 21 Oct 2026)
- **Phase / milestone:** 9 Evaluation · M0 → built in M1

## Context
Every rung is scored against the golden set, so it is the project's yardstick. Precision is the priority metric
(kickoff Q11), so the set must contain clean PRs too: a reviewer that raises alarms on clean code must be caught.
Real-only labelling would take several weekends (against "fail early", kickoff Q10); seeded-only invites "it finds what you planted".

## Decision
About 20 PRs: **~14 seeded** in a small demo repo we control (≈10 with one planted problem each, spread across security / quality / tests / docs, plus **4 clean**) **and ~6 real** merged PRs from one public open-source Python repo, each **linked to a real GitHub issue** (bug report ↔ the PR that introduced or fixed it), so their truth comes from the project's own tracker.
Labels are committed to git **before** any rung is scored (pre-registration).

## Consequences
- Positive: exact recall on the seeded part; a realism check on the real part; M1 fits in about a weekend; the demo repo doubles as the live-demo target (M9).
- Negative / cost: seeded problems reflect our idea of a bug. Reported separately from the real part, never blended into one number.
- **Real repo: `pallets/click`** (Nishant, 21 Oct 2026, `M1_REAL_REPO_PICK.md`): 77 closed bug issues, spot-checked that issues link to PRs. Runners-up: encode/httpx (64), jd/tenacity (20).
- **Built 23–24 Oct:** 5 real PRs / 6 problems (only pairs click names itself), labels by deterministic SZZ-style tracing (`golden/real/build_real.py`). Reported **per PR, no percentage** (Nishant, option A, `REAL_PRS_REVIEW.md`).

## Alternatives rejected
- Real-only: too slow to label. Seeded-only: easy to dismiss. Own repos: too few PRs and no independent truth.
