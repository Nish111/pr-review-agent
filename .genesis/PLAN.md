# PLAN — pr-review-agent

The machine-parseable implementation plan. Mirrors the milestone table in `DONE.html` (DONE.html is the
human/visual view; this is the one loops read). Sliced so each milestone ships in one L1 BUILD pass.

> Slicing rule: a milestone must have (a) a single clear outcome, (b) an exact **demo command** that
> proves it, and (c) a freeze boundary of files it may touch. If you can't write the demo command,
> the milestone is too vague — split it.

---

## Brainstorm (G0.5 — fill before slicing milestones)

> Three fundamentally different approaches to the cognitive job. Pick one. Record the rationale.
> This is the cheapest design decision — you haven't written a line of code yet.

### Approach A — The lecture's architecture, re-earned
Webhook server → queue → orchestrator running 4 grounded specialists in parallel (security, quality, tests, docs) → aggregator (dedup, score) → confidence gate → GitHub.
- Strengths: covers all 7 component groups the brief grades; natural baseline-vs-upgraded story.
- Weaknesses: most moving parts and the biggest failure surface; the live demo needs a server GitHub can reach.

### Approach B — GitHub Action, no server
Review runs inside GitHub's CI on each PR; no webhook server, queue or ingress code.
- Strengths: far less to build; free Actions minutes on public repos; most ingress failure modes disappear.
- Weaknesses: group 1 (ingress & queue) can't be demonstrated, and it's graded; fork PRs get no secrets, so no LLM key; hard to show a human approval queue.

### Approach C — Deterministic first, LLM second
Static analysers (linters, Semgrep) produce candidate findings deterministically; the LLM only verifies each against retrieved code, explains it and ranks it.
- Strengths: highest precision per unit of cost; matches the "only thinking needs an LLM" aim; very testable.
- Weaknesses: finds only what rules exist for; misses design/logic findings; weaker agent story.

### Chosen: A, with C as its first rung — the brief's improvement ladder is lint/static → single LLM → grounded specialist fan-out → confidence-routed review, so C is rung 1 of A. Each rung is measured on the same golden set, giving early numbers (fail early, kickoff Q10) and the baseline-vs-upgraded evaluation. B rejected: it removes group 1, which is graded. (Decided by Nishant, 19 Oct 2026; see G0_DRAFT.md.)

---

## Milestones

### M1 — {{M1_NAME}}
- **Outcome:** {{M1_OUTCOME}}
- **Phase (swe-master):** {{M1_PHASE}}
- **Files / freeze boundary:** `{{M1_FILES}}`
- **Demo command:** `{{M1_DEMO}}`
- **Success criteria:** {{M1_SUCCESS}}
- **Loops:** L1, L4
- **Skills:** canon + tdd + {{M1_SKILLS}}
- **Token budget:** 50000

### M2 — {{M2_NAME}}
- **Outcome:** {{M2_OUTCOME}}
- **Phase:** {{M2_PHASE}}
- **Files:** `{{M2_FILES}}`
- **Demo command:** `{{M2_DEMO}}`
- **Success criteria:** {{M2_SUCCESS}}
- **Loops:** L1, L3 (research), L4
- **Skills:** canon + tdd + {{M2_SKILLS}}
- **Token budget:** 50000

<!-- duplicate the block per milestone -->

---

## Progress (loops append here on milestone completion — newest last)

- _(none yet — first loop fills this)_
