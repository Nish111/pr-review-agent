# Pre-registration: rung 2 (one LLM reviewer)

Written 24 Oct 2026, **before** rung 2 is run. Commit this first; run after. Same discipline as rung 1 (`PREREG_RUNG1.md`).

## What rung 2 is (plain words)

One AI model reads each PR (title, description, diff, and the full changed files with line numbers) and lists
problems as JSON. Nothing else: no code search, no specialists, no second opinion. That's the brief's "single LLM reviewer" rung.

## Fixed choices (none of these may change after the first run without a new pre-registration)

| Choice | Value | Where it comes from |
|---|---|---|
| Model | **`openai/gpt-oss-120b` on Groq**, temperature 0 | S1 decision (Groq main); the model the memory project already ran on Groq |
| Prompt | `prompts/rung2_single.txt`, **sha `134aa0d267f5`** (printed on every run; a different sha means the prompt changed) | written by Claude, not tuned on any golden PR |
| Context | diff + whole changed files, trimmed to ±30 then ±10 lines if over budget | S1: ≤ 5,000 tokens per call |
| Calls | one per PR, no "ask again for a better answer"; a dropped connection is retried, a bad answer is not | memory-project rule (ADR-0001 there) |
| Output handling | strict parse; malformed or **ungrounded** findings dropped and logged, never repaired | invariant `every_posted_finding_is_grounded` |
| Scoring | same as rung 1: same file, lines within ±3; precision on all 14 seeded, recall on 10; real set per PR | `GOLDEN_SET_PLAN.md`, decision A |

## ★ One decision: the "right reason" check

Rung 1 showed (`eval/findings_rung1.md`, R2) that a location-only match can credit a finding that is in the right
place for the wrong reason. An AI reviewer writes plausible comments near changed lines, so this could inflate its recall.

**Proposal:** every finding that matches a label by location gets a second check: **does its summary describe the labelled bug?**
Both numbers are reported: location-only (comparable with rung 1) and right-reason (the honest one).

Who does the check?
- **A (recommended): you, by hand.** Expected ~5–15 matched findings, each a yes/no against the label's one-line description, in a file I prepare after the run.
  - If you follow it: the most trustworthy number, from the one person who knows code review; about 10–15 minutes.
  - Cost: it's your time on each rung (rungs 3 and 4 will need it too).
- **B: a second AI model (Gemini) judges.** No work for you, but it adds another unreliable instrument and uses quota. The memory project's M9 lesson: the instrument failed before the system did.
- **C: no right-reason check.** Location-only numbers, like rung 1. Fastest, but rung 2's recall may be overstated, and the write-up has to say so.
- **If you don't decide:** A.

**Your answer (Nishant, 24 Oct 2026):** **A and B, independently.**
- **Applied, fixed before the run:**
  - **B, the AI judge:** `gemini-3.6-flash` on Gemini, a different provider and model from the reviewer (maker ≠ checker). Prompt `prompts/judge_right_reason.txt`, **sha `971537b18244`**. Its verdicts are saved to `eval/results/rung2_judge.json` and **not printed**.
  - **A, your hand check:** `eval/HANDCHECK_RUNG2.md` lists every location-matched finding **without** the judge's verdicts. You fill it in before opening the judge file.
  - **Then compared:** `rightreason compare` prints both verdicts per finding, both right-reason recalls, and **how often you and the judge agree**. Low agreement means the judge isn't trustworthy for later rungs; that's a finding in itself (the memory project's M9 lesson).
  - **Which number is official:** yours (A) is the official right-reason number. The judge's is reported next to it, with the agreement rate.

## Prediction (written before running, so it can be wrong in public)

- **Seeded recall (location-only): 0.5–0.7.** Likely found: S01 (SQL injection), S02 (`==` on a token), S03 (path traversal),
  S07 (no test), S08 (assertion removed). Coin-flips: S04 (no transaction), S05 (N+1), S06 (UTC). Likely **missed: S09**
  (the README that's now wrong isn't in the PR, so the model never sees it) and possibly S10.
- **Seeded precision: 0.3–0.6.** Expect false alarms on the "looks risky" clean PRs: C03 (retry loop) and C04 (SQL change).
- **Right-reason recall:** 0–1 lower than location-only.
- **Real click PRs: 0–2 of 6.** The visible ones (R2 binary mode, R4) are possible; Windows/pytest-only ones aren't.
- **Calls:** 19 (14 seeded + 5 real), all under 2,000 tokens for the seeded set (measured: 624–1,791).

## How to run (after this file is committed)

Needs `GROQ_API_KEY` (reviewer) and `GEMINI_API_KEY` (judge) in the environment, the same keys the memory project uses.
1. `PYTHONPATH=src python -m pr_review eval --rung 2 --provider groq --model openai/gpt-oss-120b --click ../../click`
2. `PYTHONPATH=src python -m pr_review rightreason judge --rung 2 --provider gemini --model gemini-3.6-flash`
3. `PYTHONPATH=src python -m pr_review rightreason handcheck --rung 2`, then fill in `eval/HANDCHECK_RUNG2.md`
4. `PYTHONPATH=src python -m pr_review rightreason compare --rung 2`, only after step 3 is filled in
