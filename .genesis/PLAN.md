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

> **Order: evaluation first, fail early** (chosen by Nishant 19 Oct 2026, G5_DRAFT.md option 1: "need real precision and fail early so that the project actually works and matters"). Rungs 1–4 are all scored on the same golden set.

### M0 — Research spikes S1–S5: free LLM, free embedding model, database, golden-PR source, what videos 6–10 build
- **Outcome:** Research spikes S1–S5: free LLM, free embedding model, database, golden-PR source, what videos 6–10 build
- **Phase (swe-master):** L3 Research
- **Files / freeze boundary:** `docs/spikes/**, .genesis/decisions/**`
- **Demo command:** `ls .genesis/decisions/`
- **Success criteria:** 5 decision notes (S1–S5), each naming one choice and the evidence
- **Loops:** L3, L4
- **Skills:** canon + llmops-ai-agents, data-systems-engineering
- **Token budget:** 50000

### M1 — Contracts (Finding, Review, Job) + golden PR set v0, labels committed before any scoring
- **Outcome:** Contracts (Finding, Review, Job) + golden PR set v0, labels committed before any scoring
- **Phase (swe-master):** 1 Architecture · 9 Evaluation
- **Files / freeze boundary:** `src/pr_review/contracts/**, src/pr_review/evaluation/golden*, golden/**, tests/**`
- **Demo command:** `python -m pr_review golden check`
- **Success criteria:** ~20 PRs, every one labelled; labels' commit hash printed; Finding schema validates every label
- **Loops:** L1, L4
- **Skills:** canon + tdd, modular-architecture, llmops-ai-agents
- **Token budget:** 50000

### M2 — Rung 1: rule-based checks (linters, Semgrep) + the scorer
- **Outcome:** Rung 1: rule-based checks (linters, Semgrep) + the scorer
- **Phase (swe-master):** 9 Evaluation
- **Files / freeze boundary:** `src/pr_review/static_checks/**, src/pr_review/evaluation/**, tests/**`
- **Demo command:** `python -m pr_review eval --rung 1`
- **Success criteria:** precision and recall printed for rung 1 on the golden set; result file saved
- **Loops:** L1, L4
- **Skills:** canon + tdd, llmops-ai-agents
- **Token budget:** 50000

### M3 — Rung 2: single LLM reviewer: reused provider layer, budget guard, basic trace
- **Outcome:** Rung 2: single LLM reviewer: reused provider layer, budget guard, basic trace
- **Phase (swe-master):** 5 LLM & Reasoning · 16 Economics
- **Files / freeze boundary:** `src/pr_review/llm_client/**, src/pr_review/trace/**, src/pr_review/specialists/single*, tests/**`
- **Demo command:** `python -m pr_review eval --rung 2`
- **Success criteria:** rung 2 numbers next to rung 1; zero paid calls; a trace per review
- **Loops:** L1, L4
- **Skills:** canon + tdd, llmops-ai-agents, production-readiness
- **Token budget:** 50000

### M4 — Ingress & queue per FAILURE_MATRIX_01_INGRESS (group 1)
- **Outcome:** Ingress & queue per FAILURE_MATRIX_01_INGRESS (group 1)
- **Phase (swe-master):** 3 Backend · 12 Reliability
- **Files / freeze boundary:** `src/pr_review/webhook_receiver/**, src/pr_review/job_queue/**, src/pr_review/store/**, tests/ingress/**`
- **Demo command:** `pytest tests/ingress -q`
- **Success criteria:** T1–T16 pass; T7/T8/T10/T12 baseline-vs-ours numbers recorded
- **Loops:** L1, L2, L4
- **Skills:** canon + tdd, distributed-systems, security-engineering
- **Token budget:** 50000

### M5 — Code index + hybrid search (groups 2, 3)
- **Outcome:** Code index + hybrid search (groups 2, 3)
- **Phase (swe-master):** 6 Memory · 14 Data
- **Files / freeze boundary:** `src/pr_review/ingestion/**, src/pr_review/retrieval/**, src/pr_review/embedder/**, tests/**`
- **Demo command:** `python -m pr_review search "verify_token"`
- **Success criteria:** exact-name and similar-code hits with file:line; incremental refresh re-embeds only changed files
- **Loops:** L1, L4
- **Skills:** canon + tdd, data-systems-engineering
- **Token budget:** 50000

### M6 — Rung 3: 4 grounded specialists in parallel (group 4)
- **Outcome:** Rung 3: 4 grounded specialists in parallel (group 4)
- **Phase (swe-master):** 4 Orchestration · 8 Multi-agent
- **Files / freeze boundary:** `src/pr_review/specialists/**, src/pr_review/orchestrator/**, tests/**`
- **Demo command:** `python -m pr_review eval --rung 3`
- **Success criteria:** rung 3 numbers next to rungs 1–2; ungrounded findings dropped and traced; partial runs reported as partial
- **Loops:** L1, L2, L4
- **Skills:** canon + tdd, llmops-ai-agents, distributed-systems
- **Token budget:** 50000

### M7 — Rung 4: aggregator + approval queue + confidence calibration (group 5)
- **Outcome:** Rung 4: aggregator + approval queue + confidence calibration (group 5)
- **Phase (swe-master):** 19 HITL
- **Files / freeze boundary:** `src/pr_review/aggregator/**, src/pr_review/hitl/**, tests/**`
- **Demo command:** `python -m pr_review eval --rung 4 && python -m pr_review queue`
- **Success criteria:** threshold chosen from golden-set data (target ≥ 90% precision); pending reviews listed; dispute path works
- **Loops:** L1, L4
- **Skills:** canon + tdd, llmops-ai-agents
- **Token budget:** 50000

### M8 — Traces, cost report, audit trail (group 6)
- **Outcome:** Traces, cost report, audit trail (group 6)
- **Phase (swe-master):** 10 Observability · 15 Governance
- **Files / freeze boundary:** `src/pr_review/trace/**, src/pr_review/reports/**, tests/**`
- **Demo command:** `python -m pr_review trace <review_id>`
- **Success criteria:** every step with cost, latency, confidence, human decision; static HTML report
- **Loops:** L1, L4
- **Skills:** canon + tdd, production-readiness
- **Token budget:** 50000

### M9 — Live PR → review demo (real GitHub App), ADRs, write-up
- **Outcome:** Live PR → review demo (real GitHub App), ADRs, write-up
- **Phase (swe-master):** all
- **Files / freeze boundary:** `docs/**, src/pr_review/github_client/**, README.md`
- **Demo command:** `python -m pr_review demo --live`
- **Success criteria:** a recorded live run + the final baseline-vs-upgraded table + ADRs
- **Loops:** L1, L4
- **Skills:** canon + production-readiness, security-engineering
- **Token budget:** 50000



---

## Progress (loops append here on milestone completion — newest last)

- **M0 done (21 Oct 2026):** S1–S4 accepted, S5 provisional (`.genesis/decisions/`). Commit abf09b2.
- **M1 done (24 Oct 2026):** contracts + 14 seeded PRs (10 problems, 4 clean) + 5 real click PRs (6 problems); `python -m pr_review golden check` OK; seeded labels committed in 3d9e146 before any scoring. Real set reported per PR (option A).
- **M2 done (24 Oct 2026):** rung 1 (ruff, pre-registered in a3f9a72). Seeded: precision 0.22, recall 0.20. Real: 0/6 understood (R2 1/2 by a location-only coincidence). `eval/findings_rung1.md`.
