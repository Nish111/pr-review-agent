# OSPREY: handoff for the PR Review Agent chat

**Trigger word: OSPREY.** Written 18 Oct 2026 at the end of the memory-project M9 chat. Scope of an
OSPREY chat: **the PR Review Agent only** (W8 deliverable). The memory project continues under
KESTREL; LinkedIn, SBL and outreach are separate chats.

> **STATUS 7 Nov 2026 (read this first).** M0–M6 done (rung 3 in `eval/findings_rung3.md`). M7 code built; `eval/PREREG_RUNG4.md` answered; next: run rung 4 (no model calls). Live pointer: `.genesis/checkpoints/CURRENT.md`.
>
> **Earlier status, 27 Oct 2026.** M0–M5 done. M5: code index + hybrid search, real model bge-small (S2 amended: jina fails with transformers 5). Next: M6 (rung 3 specialists). Live pointer: `.genesis/checkpoints/CURRENT.md`.
>
> **STATUS 25 Oct 2026 (read this first).** M0–M4 done. M4 = ingress & queue on SQLite (`src/pr_review/webhook_receiver`, `store`, `job_queue`), tests T1–T16 in `tests/ingress`, before/after numbers in `FAILURE_MATRIX_01_INGRESS.md` §6 (v4). Next: M5 index & search. Live pointer: `.genesis/checkpoints/CURRENT.md`.
>
> **STATUS 19 Oct 2026 (read this first in a new OSPREY chat).** Genesis setup G0–G5 is complete in this repo
> (github.com/Nish111/pr-review-agent). Decisions: approach A (lecture architecture) with C (rule-based checks)
> as rung 1; no confidence threshold until the golden set exists; milestone order = evaluation first (M0 spikes →
> M1 golden set → M2 rung 1 → … → M9 live demo). The ingress failure matrix is at v3. `.genesis/checkpoints/CURRENT.md`
> points at M0. Scratch file: `Temp10.md`. Decision records: G0_DRAFT.md, G5_DRAFT.md, KICKOFF_ANSWERS_DRAFT.md.
> The sections below are the original 18 Oct handoff, kept for history; §1 and §2 are superseded by the above.

**Read in this order:** this file → `../KICKOFF_PR_AGENT.md` (your 18 Sep kickoff; still right on
scope, method and DoD) → `../LMS_Archive/docs/week-8-pr-review-agent-build.md` (the brief, complete)
→ `../PLAN_FROM_HERE.md` §4 (when this fits).

---

## 1 · Where it stands

| | state |
|---|---|
| Brief | captured in full (`LMS_Archive/docs/week-8-pr-review-agent-build.md`). No due date; W8 submission form not open (11 Oct capture) |
| Lecture (stated prerequisite) | **not watched.** Recordings 18 and 19 Jul, Drive folder `12y48Ce_5m_yJ8pizM1ZDbMmWVPCnfYMe` |
| Design write-up `pr-review-agent.html` | **found on disk 18 Oct** at `Antern\Session15-16\` (full text). Design + 23-module map, no code, no repo link. See `STEP3_FIND_BASELINE.md` |
| Supplied baseline | **resolved 19 Oct: no code supplied.** Baseline = html design + videos 6-10 (see `STEP3_FIND_BASELINE.md` Outcome). Was: not located. Brief §1 requires starting from it and keeping it for the before/after story |
| Genesis kit | at `D:\Nishant\Learnings_NewLaptop\Antern\Genesis\genesis-kit-main\` (outside the connected folder) |
| Source docx | `D:\Nishant\Learnings_NewLaptop\Antern\Session8\AI_PR_Review_Agent_Project_Brief.docx` (outside the connected folder) |
| Repo | none yet. This folder (`10-PR-Review-Agent/`) is a placeholder for the handoff only; the Genesis repo goes wherever you decide (D1) |
| Plan slot | `PLAN_FROM_HERE.md` puts it in weeks 5-8 (from 11 Nov), after M10, positioning and outreach. Starting earlier is your call (D3) |

Public reference, not to copy: a cohort-mate's repo, `github.com/sadaka/ai_pr_review` ("four grounded
specialist agents"; Discord `content.md` line 449). The brief says the reference project is "a
scaffold, not an answer to copy". Reading it after your own failure matrices are written is fine;
before is what the brief warns against.

## 2 · The first session, one step at a time (nothing else in session 1)

1. **Grant the new chat access** to `D:\Nishant\Learnings_NewLaptop\Antern\` (it will ask): the
   docx, the Genesis kit and `Session15-16\pr-review-agent.html` live there.
2. **Download and read `pr-review-agent.html`** (Drive link in NEEDS_MANUAL_DOWNLOAD row 20). Its
   section "From design to code" is the likeliest description of the baseline.
3. **Locate the supplied baseline.** In order: the html; the two W8 recordings' descriptions; Discord
   `questions-for-ayush.md` / `technical-question.md`; then ask in Discord. Until found, nothing in
   the evaluation section (baseline-vs-upgraded) can be designed.
4. **Write the component list + ONE failure matrix** (group 1, ingress), in the brief's six-row form.
   That is session 1's whole output.

## 3 · Decisions you'll be asked (options and consequences come as a form in that chat)

- **D1 · Repo location**: inside `AI-Sprint-Execution\10-PR-Review-Agent\` (next to everything, one
  connected folder) or a separate folder (cleaner git, needs its own connection).
- **D2 · Golden PR set source**: your own public PRs, a public OSS repo with known-bad merges, or
  synthetic. This is evaluation group 7 and the largest single cost (KICKOFF: "days, not hours").
- **D3 · Start now or after M10**: the plan says after; outreach is calendar-bound and goes first
  whatever you choose.

## 4 · Reuse from the memory project (copy, don't rewrite; all in `05-Memory-Intelligence-System/`)

| need in the brief | reuse | why it's worth it |
|---|---|---|
| provider calls, retries, budget guard | `incident_memory/spikes/extraction.py` (`_post`, 503 = one retry, per-minute vs daily 429, credential scrubbing) | cost ~5 quota days to get right (`eval/m9_build_log.md` 13-17 Oct) |
| quota gate before any generation | `tools/label_sample_t2.py` `preflight` / `preflight baseline` | reads requests actually sent from the trace |
| traces (DoD item 6) | `incident_memory/trace.py` + `trace_view.py` (OTel GenAI fields, http_attempts, never raises) | the DoD's trace list is a superset of M9's events |
| durable review truth / audit trail | `incident_memory/store.py` supersession log + `tools/store_dump.py` | append-only with a readable diff |
| checkpoint / resume | `baseline --fresh-since` pattern; the M4 bug where a cached failure was reused as a success | don't re-learn it |
| evaluation discipline | pre-registration in its own commit, blind owner labels with cited evidence, blast radius | M8/M9: the instrument fails before the system does |

**One finding to carry in, from M9:** the trace flagged 1 of 5 human-judged failures; the 4 misses
were refusals in a phrasing the detector didn't know (`eval/findings_m9.md` headline). For a PR
reviewer, "confidence-routed review" and HITL escalation depend on exactly that kind of detector.
Budget for testing it against human labels, not only against itself.

## 5 · Working rules (same as every chat)

Claude never deletes files; never runs git (you do); zero cost, free tiers; pre-registration commits
before the code it constrains; maker ≠ checker; blast radius before adopting an instrument change;
one step at a time; explain what was done and what it means; decisions give the consequence of
following, of not following, and of not deciding; files with steps for anything you must check;
push back when you're wrong; never infer the time of day.
