# M0 · Research spikes S1–S5

Started 19 Oct 2026 (you chose to start now rather than wait for 11 Nov).

## What M0 is and why it comes first

Before building anything, five questions must be answered, because each one changes what gets built.
A **spike** is a short, time-boxed investigation that ends in **one decision note** in `.genesis/decisions/`.
M0 is done when all five notes exist (the demo command is `ls .genesis/decisions/`).

**Existence pre-flight** (Genesis's "is it already built?" check): nothing of the PR agent exists yet. Two
things from the memory project already exist and shape the answers below:
- its LLM provider layer already supports **Groq, Gemini, OpenRouter and Ollama**, with free-tier limits measured on real runs (`05-Memory-Intelligence-System/incident_memory/extraction/profiles.py`);
- its store is **SQLite**, built into Python with nothing to install.

## Who does what

| Spike | Question | Who | Status |
|---|---|---|---|
| S1 | Which free LLM can carry the review workload? | Claude | **decided** → `.genesis/decisions/S1-free-llm.md` |
| S2 | Which free embedding model for code search? | Claude | **decided** → `.genesis/decisions/S2-embedding-model.md` |
| S3 | Which database? | Claude | **decided** → `.genesis/decisions/S3-database.md` |
| S4 | Where do the golden PRs come from? | Nishant | **decided** → `.genesis/decisions/S4-golden-pr-source.md` |
| S5 | What does the instructor build in videos 6–10? | Nishant (watching) | **provisional** → `.genesis/decisions/S5-baseline.md`; final after your video notes |

---

## S1 · Free LLM: the analysis (superseded by the decision note, which corrects the numbers)

> **Correction, 21 Oct:** Groq also has a **daily** limit of 200,000 tokens per model (published table, read 16 Oct). That, not the per-minute rate, is the real bottleneck. The decision note works it through: 2 Groq models in rotation, one scored run per rung, and stability measured on a 5-PR subset.

**The workload, counted** (golden set ~20 PRs, each rung scored ~3 times to check stability):
- rung 2 (single reviewer): 20 PRs × 1 call × 3 runs = **60 calls**
- rung 3 (4 specialists): 20 × 4 × 3 = **240 calls**
- rung 4 (aggregate + calibrate): mostly no new LLM calls
- **≈ 300 calls per full evaluation**, each roughly 3,000–6,000 tokens (diff + retrieved code + instructions)

**Against the limits you already measured:**

| Provider | Measured free limit | Full evaluation (~300 calls) takes | Fit |
|---|---|---|---|
| Gemini | 20 requests/day | ~15 days | ✗ too small to be the main model |
| OpenRouter (free models) | 50 requests/day | ~6 days | ✗ as main; ✓ as a second opinion |
| Groq | 30 requests/min, **8,000 tokens/min per model** | ~1–3 hours | ✓ main candidate, **but** any single call over 8,000 tokens fails outright (the 413 error from M9) |
| Ollama (local) | no quota | depends on your laptop | ✓ if your hardware can run a code model |

**What this means for the design:** the free tier sets a hard **context budget**: every review call must stay
under ~6,000 tokens (diff + retrieved code + prompt), leaving room for the answer. That's not a nuisance,
it's the brief's group 3 requirement ("context-budget control") arriving for a concrete reason. Retrieval must pick the *best* few code slices, not dump everything.

**Lean:** Groq as the main model; a *different* model (Gemini or OpenRouter) as the checker on small samples
(maker ≠ checker); Ollama as the no-quota fallback **if** your laptop can run it. Still to verify: Groq's
*daily* token limit for the chosen model (not yet measured in M9).

## S2 · Free embedding model

An **embedding model** turns code into a list of numbers so that similar code can be found by search.
The html uses OpenAI's paid one. Free options run **locally** (no quota, no network), e.g. small open models via
the `sentence-transformers` Python package, or `nomic-embed-text` through Ollama. Whether these are practical depends on the same fact as S1: your laptop's memory.

## S3 · Database: the lean

**Lean: SQLite** for everything: jobs, reviews, findings, the event trail, **and** search:
- **keyword / exact-name search:** SQLite's built-in full-text search (FTS5), which finds `verify_token` exactly;
- **similar-code search:** the `sqlite-vec` add-on (free, installed with pip).

Why: zero cost, nothing to install or run, the memory project's store code is SQLite already, and one
file holds everything (the html's own argument for "one store, not three", ADR-003, without the cloud
account). Tiger Cloud / Postgres stays behind the store interface as the paid/scale option (your Q1).
This becomes a decision note once S2 confirms the embedding size works with `sqlite-vec`.

---

## Your one step: the fact S1 and S2 need

Your laptop's hardware decides whether the local, no-quota options (Ollama, local embeddings) are usable.
(I can't see it: the shell I use runs in a small virtual machine, not on Windows itself.)

**How to find it (Windows):** press `Ctrl + Shift + Esc` → **Task Manager** → **Performance** tab.
- click **Memory** → note the total (e.g. "16 GB");
- click **GPU** (if listed) → note the name (e.g. "NVIDIA RTX 3050, 4 GB") or "Intel UHD only".

Write both here:
- **RAM (Nishant, 21 Oct):** 16 GB
- **GPU (Nishant, 21 Oct):** Intel Iris Xe Graphics (integrated; 1.6 GB dedicated / 7.9 GB shared), no NVIDIA GPU
- **→ Result:** the middle case. Local embeddings are fine; a local LLM works but slowly, so it's the fallback only, and Groq is the main model.

**What each answer leads to:**
- **16 GB+ RAM, any NVIDIA GPU:** local model + local embeddings are practical. Quota stops being a worry.
- **8–16 GB, no NVIDIA GPU:** local embeddings fine; a local LLM works but slowly, so it's the fallback only, and Groq stays the main model.
- **under 8 GB:** everything that thinks goes to Groq; embeddings use the smallest local model.
- **If you don't check:** I assume the middle case. If that's wrong, S1/S2 get redone once the real numbers show up.

---

## Glossary

| Term | Meaning |
|---|---|
| **Spike** | a short investigation that ends in one decision note |
| **Existence pre-flight** | Genesis's check that the milestone isn't already built |
| **Context budget** | the maximum size of what's sent to the model in one call |
| **413 / 429** | HTTP errors: request too large (can't be retried as-is) / too many requests (wait and retry) |
| **TPM / RPM / RPD** | tokens per minute / requests per minute / requests per day |
| **Token** | the unit LLMs count text in, roughly ¾ of a word |
| **Embedding model** | turns text or code into numbers so similar items can be found |
| **Ollama** | free software that runs open AI models on your own computer |
| **SQLite / FTS5 / sqlite-vec** | a database stored in one file, built into Python / its full-text search feature / a free add-on for similarity search |
| **Maker ≠ checker** | the model that produces a result is never the one that verifies it |

---

## S4 · ★ Your decision: where the golden PRs come from

**What the golden set is:** ~20 PRs where we already know the right review. Every rung is scored against it, so it's the yardstick for the whole project. Because precision is your priority (Q11), it must also include **clean PRs with nothing wrong**: a reviewer that raises alarms on clean code fails precisely there.

| Option | What it is | Good | Bad |
|---|---|---|---|
| **A · Real PRs from a public open-source Python repo** | merged PRs that were later fixed by a bug-fix commit, so we *know* they had a problem | realistic; the brief's own wording ("real merged PRs where you know which were bad") | slow: each needs your reading to label; some "bugs" need deep repo knowledge |
| **B · Seeded PRs** | take a small clean repo and write PRs with **planted** problems (an SQL injection, a missing test, a stale docstring), plus some clean PRs | exact answers known in advance; fast; covers all 4 specialists on purpose | less realistic; risk of building a reviewer that only finds the kind of bugs we plant |
| **C · Your own repos** | PRs from the memory project etc. | you know the code | few PRs, no known-bad ones; you'd be judging your own code |

**Recommendation: B + A mix.** About **14 seeded** (10 with planted problems spread across security/quality/tests/docs, **4 clean**) **+ 6 real** from one public repo as a realism check.
- **If you follow it:** M1 is doable in about a weekend; recall is measured exactly on the seeded ones; the 6 real ones show whether the result survives contact with real code. The write-up can say both.
- **If you pick A only:** most realistic, but labelling ~20 real PRs is several weekends and pushes M2's first numbers back (against your "fail early").
- **If you pick B only:** fastest, but the evaluation can be dismissed as "it finds what you planted".
- **If you pick C:** not recommended. Too few PRs, and no independent truth.
- **If you don't decide:** M1 can't start, and M0 stays open.

**Your answer (Nishant, 21 Oct):** B + A mix. Better to start building and show demo results, and also involve real open-source issues.
- **Applied:** the real part (A) uses merged PRs that are **linked to real GitHub issues** (a bug report → the PR that caused it or fixed it), so the "right answer" comes from the project's own issue tracker, not from us. Written into `.genesis/decisions/S4-golden-pr-source.md`.
