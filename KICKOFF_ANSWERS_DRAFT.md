# Genesis kickoff interview: answers (confirmed by Nishant, 19 Oct 2026)

> **Status:** done. All 12 agreed; notes added on Q1, Q10, Q11 and Q12. Written into `.genesis/decisions/decisions-manifest.md`.

Written 19 Oct 2026.

## What we're doing and why

The repo now exists, with the Genesis structure in `.genesis/`. Genesis's first step is a **kickoff
interview**: 12 questions (in `.genesis/KICKOFF-INTERVIEW.md`) that pull the assumptions out of your
head before any planning starts. The answers become `.genesis/decisions/decisions-manifest.md`, which
is the input to **G0**, the first stage of the Genesis ritual (G0–G6 = the seven setup stages: scope,
invariants, definition of done, milestones, and so on).

Normally the agent asks the 12 questions one at a time. To save your time, I've **pre-filled a
suggested answer** for each one from what we already know: the brief, your working rules, and the
plan. Most are facts, not decisions. **Only the 4 marked ★ really need your thinking.**

## What you do

1. Read each question and my suggested answer.
2. If you agree, leave it. If not, write yours on the "Your answer" line (any format, I'll tidy it).
3. For the 4 ★ questions, write at least "agree" or your change.
4. Say "kickoff answers done". I then write `decisions-manifest.md` and commit-ready files, and give you the git commands.

---

### Trade-offs

**Q1 ★ · Rank speed, maintainability, cost, reliability.**
- Suggested: **1 cost · 2 reliability · 3 maintainability · 4 speed.**
- Why: cost first because your rule is zero cost / free tiers. A design that needs paid APIs fails
  before it starts. Reliability second because the brief grades failure handling. Speed last:
  a review can take minutes, the brief only demands the *acknowledgement* in < 10 s.
- If you follow it: every architecture choice will pick the free option, even when it's slower (e.g. a local embedding model).
- If you don't (e.g. speed first): paid, fast providers become acceptable, which breaks the zero-cost rule.
- If you don't decide: Genesis has no tie-breaker, and each architecture choice comes back to you as a separate question.
- **Your answer (Nishant):** agree. Keep zero cost, but keep the design flexible enough to add paid tiers later. If that turns out not to be possible, say so, so a different plan can be chosen.
  - **Claude:** it is possible, and it's cheap to keep possible. Every paid-vs-free choice (LLM provider, embedding model, database) sits behind one small interface, so moving to a paid tier is a config change, not a rewrite. Recorded as assumption 1 in the manifest.

**Q2 · Scale now vs in 12 months.**
- Suggested: now = 1–2 demo repos, a few PRs a day, a golden set of ~20–50 PRs. In 12 months = the
  same. It's a cohort deliverable and portfolio piece, not a product with users.
- **Your answer (Nishant):** agree

**Q3 · Prototype, internal tool, or production system?**
- Suggested: **production-shaped prototype**. Built with production habits (failure matrices, tests,
  traces, as the brief requires), run at prototype scale.
- **Your answer (Nishant):** agree

### Non-obvious assumptions

**Q4 · Performance limits you'd notice immediately.**
- Suggested: GitHub's acknowledgement within 10 s (hard, from GitHub). A full review within ~5 minutes
  (soft). A test suite that runs locally in under 2 minutes, so you actually run it.
- **Your answer (Nishant):** agree

**Q5 · Brand or UX feel.**
- Suggested: review comments read like a **careful senior reviewer**: short, specific, each with
  file + line + evidence, no praise padding. Any dashboard is plain and dense; looks don't matter here.
- **Your answer (Nishant):** agree

**Q6 · What happens on failure.**
- Suggested: **degrade to slower but correct, never fast but wrong** (the lecture's rule). Developer-facing
  messages are honest and never promise a time (your F16 answer). Nothing is silently dropped (dead-letter shelf + sweeper).
- **Your answer (Nishant):** agree

### Integration points

**Q7 · Systems it touches.**
- Suggested: GitHub (webhooks in; PR files, diffs and comments via the GitHub API; reviews posted back).
  One or more free LLM (Large Language Model) providers, reusing the provider layer from the memory project.
  A local database + vector search. Local Redis (or a stand-in) for the queue.
- **Your answer (Nishant):** agree

**Q8 · Who can do what.**
- Suggested: only repo members can trigger `/review` (F17). Only a human can approve a review held in the
  approval queue. The bot never approves or merges a PR, it only comments.
- **Your answer (Nishant):** agree

**Q9 · Compliance or legal limits.**
- Suggested: no secrets or tokens in logs (F15). Code from private repos is never sent to a provider that
  trains on inputs. Use only public or your own repos for the golden set.
- **Your answer (Nishant):** agree

### Risk and failure modes

**Q10 ★ · The single most likely way this project fails.**
- Suggested: **the evaluation never gets built.** The golden PR set ("days, not hours") gets pushed to the
  end, and the project ships an agent with no proof it beats the baseline. That fails the brief's definition of done.
- If you agree: the golden set becomes an early milestone (M2 or M3), not the last one.
- If you don't: it stays near the end, where it's most likely to be squeezed.
- If you don't decide: milestone order defaults to the html's 20-phase order, where evaluation is phase 9 of 20.
- **Your answer (Nishant):** agree. If it's going to fail, it should fail early, so there's time to change things.
  - **Effect:** the golden PR set and a first baseline-vs-upgraded run come early in the milestone order.

**Q11 ★ · The one thing you'd be embarrassed to ship.**
- Suggested: **a confident, wrong finding.** For example, the bot flags a security bug in code that's
  fine, or cites a file it never read. This is what the "confidence-routed" gate and grounding exist to prevent.
- If you agree: the evaluation measures **precision** (how many of its findings were right) before **recall** (how many real problems it found).
- If you don't: e.g. "missing a real bug" instead, so the reviewer is tuned to say more, and noise rises.
- If you don't decide: no quality bar, so "good enough" gets decided late and under time pressure.
- **Your answer (Nishant):** agree. Precision and recall both matter, but here precision is the priority.

**Q12 ★ · Known unknowns (each becomes a research spike before M1).**
- Suggested, from the work so far:
  1. which **free** LLM gives usable review quality inside free-tier limits;
  2. which free **embedding model** (turns code into numbers for search) replaces the html's paid OpenAI one;
  3. Tiger Cloud free tier vs plain local Postgres + pgvector (the vector search add-on);
  4. where the golden PRs come from (your own repos, a public open-source repo, or synthetic). This is D2 in the handoff;
  5. what the instructor actually builds in videos 6–10. That's the "baseline" we must improve on.
- If you agree: 5 short spikes before M1. Each ends in one decision note.
- If you don't: these get decided mid-build, and they'd likely force rework.
- If you don't decide: same as not agreeing.
- **Your answer (Nishant):** agree. Better to start, go slowly and make a real difference than to do rework.

---

## Glossary

| Term | Meaning |
|---|---|
| **Genesis** | the cohort's repo kit: it adds a `.genesis/` folder holding the plan, definition of done, decisions and loop rules, so the AI agent works from written state |
| **G0–G6** | the seven Genesis setup stages, run once before any coding |
| **decisions-manifest.md** | the file these answers become; G0 reads it |
| **Research spike** | a short, time-boxed investigation that ends in one decision |
| **Golden PR set** | real PRs where we already know the right review; used to score the agent |
| **Precision / recall** | of the findings it raised, how many were right / of the real problems, how many it found |
| **Embedding model** | a model that turns text or code into a list of numbers, so similar code can be found by search |
| **pgvector** | a free add-on that lets Postgres (a database) do that similarity search |
| **LLM** | Large Language Model |
