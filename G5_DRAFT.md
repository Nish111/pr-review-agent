# Genesis G5: the milestone plan (done 19 Oct 2026: option 1, evaluation first)

Written 19 Oct 2026.

## Where we are

| Stage | What it is | Status |
|---|---|---|
| G0 / G0.5 | locked spec + chosen approach | done (committed) |
| G1 | `.genesis/` structure | done (the scaffold commit) |
| **G2** | the dependency map + the "never broken" rules | **done now, by me: no decisions needed** (details below) |
| **G3** | pointers to the Genesis kit's knowledge pages | **done now, by me** |
| **G4** | definition of done: the checklist every milestone must pass | **done now, by me** |
| **G5** | the milestone list, in order | **this file: one decision** |
| G6 | prime the first loop | after G5 |

### What G2–G4 contain (read-only, for your information)

- **G2 · `.genesis/context-graph.json`:** 18 modules and which may use which (41 links, checked: no
  circular dependencies). Plus **5 rules that must never break**, each with the test that proves it:
  1. every finding points to code the bot actually read, otherwise it's dropped (your Q11);
  2. one review job per PR commit, even under 50 simultaneous webhooks (ingress F8/F9);
  3. the bot never approves or merges, and nothing auto-posts until the threshold is calibrated (your Q8 + field 5);
  4. every call to an outside service has a timeout and a failure path;
  5. dependencies point inward: the core data shapes depend on nothing.
- **G3 · `.genesis/wiki/index.md`:** pointers to 5 Genesis-kit topic areas (architecture, distributed systems, data, LLM ops, security), plus our own files.
- **G4 · `.genesis/DONE.html` section 2:** 8 checks every milestone must pass (e.g. `ruff check .` clean and
  `pytest -q` green, no paid API calls, a separate model verifies) + 6 checks tied to specific milestones +
  2 kit checks that **don't** apply, with the reason: no dashboard UI, no cloud deploy.
  - **Language: Python.** Not a new decision: it's the only way to reuse the memory project's provider layer, pacing and trace code, which the handoff lists as a reuse.

---

## G5 · What a milestone is

A milestone is one chunk of work with **one outcome** and **one command that proves it works** (the
"demo command"). If we can't write the command, the milestone is too vague. Each one below says what you'd see when you run its command.

## ★ The decision: in what order?

### Option 1 (recommended): evaluation first, "fail early"

| # | Milestone | Brief group | Demo command → what you'd see |
|---|---|---|---|
| M0 | 5 research spikes (free LLM, free embedding model, database, golden-PR source, what videos 6–10 build) | — | `ls .genesis/decisions/` → 5 short decision notes |
| M1 | Data shapes (`Finding`, `Review`, `Job`) + **golden PR set v0** (~20 PRs, labels committed *before* any scoring) | 7 | `python -m pr_review golden check` → "20 PRs, 20 labelled, labels committed in <hash>" |
| M2 | **Rung 1**: rule-based checks (linters, Semgrep) + the scorer | 7 | `python -m pr_review eval --rung 1` → precision and recall numbers |
| M3 | **Rung 2**: single LLM reviewer, with the reused provider layer, budget guard and trace | 4, 6 | `eval --rung 2` → numbers next to rung 1 |
| M4 | Ingress & queue, per the failure matrix | 1 | `pytest tests/ingress -q` → T1–T16 pass; T8 baseline vs ours shown |
| M5 | Code index + hybrid search | 2, 3 | `python -m pr_review search "verify_token"` → exact-name and similar-code hits, with file:line |
| M6 | **Rung 3**: 4 grounded specialists in parallel | 4 | `eval --rung 3` → numbers next to rungs 1–2 |
| M7 | **Rung 4**: aggregator + approval queue + confidence calibration | 5 | `eval --rung 4` + `python -m pr_review queue` → threshold chosen from data, pending reviews listed |
| M8 | Traces, cost report, audit trail | 6 | `python -m pr_review trace <review_id>` → every step with cost, time, confidence |
| M9 | Live PR → review demo (real GitHub App), ADRs, write-up | all | a recorded demo + the final baseline-vs-upgraded table |

- **If you follow it:** real precision/recall numbers exist by M2, early. If the LLM rungs don't beat the
  rule-based rung, you find out at M3 instead of M9 (your Q10: "fail early"). Every later milestone is measured against a fixed yardstick.
- **Cost:** the golden set (M1) is the slowest, least exciting work, and it comes first.

### Option 2: the html's build order (system first, evaluation later)

Ingress → index → retrieval → specialists → aggregator → HITL → **then** golden set and evaluation (html phase 9 of 20).
- **If you choose it:** the system looks impressive sooner, and it's easier to demo mid-way.
- **But:** the first real numbers arrive near the end. If they're bad, there's no time left to change course, which is exactly the failure you named in Q10.

### If you don't decide
Nothing can be sliced into `PLAN.md`, and G6 (starting the first loop) can't happen. The project stays at setup.

## An honest timing note (pushing back)

Your plan gives this project weeks 5–8 (from 11 Nov): about **4 weeks × (~1.5 h weekdays + ~7 h weekend) ≈ 34 hours**.
Ten milestones in 34 hours is tight; the golden set alone is "days, not hours". Realistic reading:
- M0–M4 fit in weeks 5–6; M5–M7 in weeks 7–8; **M8–M9 land in the plan's buffer weeks 9–10.**
- If time runs short, the safe cut is **M8's polish** (keep basic traces, which the brief requires; drop the cost report's extras), **not** the evaluation.

## What you do

Write `1` or `2` on the line below (or your own order), then say **"G5 done"**. I'll write the
milestones into `.genesis/PLAN.md` and `DONE.html` section 3, and give you the git commands.

- **Your answer (Nishant):** option 1. "Need real precision and fail early, so that the project actually works and matters." → Written into `.genesis/PLAN.md` and `DONE.html` section 3.

---

## Glossary

| Term | Meaning |
|---|---|
| **Milestone (M0–M9)** | one chunk of work with one outcome and one demo command |
| **Demo command** | the exact command that proves a milestone works |
| **Rung 1–4** | the brief's improvement ladder: rule-based checks → single LLM → grounded specialists → confidence-routed review |
| **Golden PR set** | PRs where we already know the right review; the fixed yardstick for every rung |
| **Pre-registered labels** | the "right answers" are committed to git *before* scoring, so they can't be adjusted afterwards to flatter a result |
| **Spike** | a short, time-boxed investigation ending in one decision note |
| **Semgrep** | a free rule-based code scanner |
| **ruff / pytest** | Python's fast code checker / test runner |
| **ADR** | Architecture Decision Record |
| **Context graph** | `.genesis/context-graph.json`: modules, which may use which, and the never-break rules |
