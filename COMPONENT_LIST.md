# PR Review Agent · Component list (step 4, part 1)

Written 19 Oct 2026 from three sources that each slice the system differently:
**V1** = your notes on video 1 (`PR Agent Doc.docx`), **HTML** = `Antern\Session15-16\pr-review-agent.html`,
**BRIEF** = the 7 component groups in `AI_PR_Review_Agent_Project_Brief.docx`.

## Why three lists, and which one we use

- Video 1 says the design has **5 components** (orchestrator, events, retriever, gates, agents), and
  that "these 5 components will run the same loop 5 times". That is the *failure-mode loop*.
- The html has **23 code modules**. That's how the code is laid out, not the list to analyse.
- The brief has **7 groups**. These are what gets graded: one failure matrix per material component.

**Decision taken (reversible): failure matrices follow the brief's 7 groups.** That's what gets graded,
and each lecture component fits inside a group (table below). If videos 2-5 show the instructor
using the 5-component split for the matrices, we re-cut. The content doesn't change, only the headings.

## The crosswalk

| # | Brief group | Lecture component (V1) | HTML modules | Contract (one line) |
|---|---|---|---|---|
| 1 | Ingress & queue | (before orchestrator) | `webhook_receiver/`, `job_queue/`, `reliability/idempotency` | GitHub `pull_request` webhook in → HMAC verified, deduped on `X-GitHub-Delivery`, enqueued, **200 within 10s** |
| 2 | Ingestion & index | retriever (write side) | `data/ingestion`, `data/freshness`, `migrations` | repo files → chunks + embeddings in `code_chunks`; only changed files re-embedded |
| 3 | Retrieval & grounding | retriever (read side) | `memory/` (`context_retriever`, `embedder`, `tiger_client`) | diff → hybrid (vector + keyword/exact-identifier) top-k chunks, each with path for citation |
| 4 | Workflow & specialists | orchestrator + agents | `orchestrator/`, `core/workflow_engine`, `agents/`, `tools/`, `prompts/` | one job → 4 parallel specialists (security, quality, tests, docs) → `Finding[]` each; checkpoint per node |
| 5 | Aggregation & HITL | gates | `agents/contracts`, aggregator node, `hitl/` | 4 × `Finding[]` → deduped, scored review → auto-post **or** human approval queue |
| 6 | Data, proof & economics | events | `observability/`, `economics/`, `database/`, `security/` audit | every span / LLM call / cost / decision appended to `agent_events`; BudgetGuard blocks over-budget |
| 7 | Evaluation & learning | (the verifier, outside the 5) | `evaluation/` (`golden_dataset`, `judge`, `regression_gate`) | golden PRs → precision/recall of baseline vs upgraded; regression gate blocks a worse prompt |

`Finding` contract (HTML 3.4): `agent_type, severity, category, summary, file_path, line_start, line_end,
suggestion, confidence, rationale`.

## Things the html assumes that clash with your rules (not decided yet — flag only)

<!-- TODO (Nishant): no action today. These become decisions when we reach group 2/3. -->
- **Paid embedding model:** the html uses OpenAI `text-embedding-3-large`. Your rule is zero cost /
  free tiers. Likely direction: a local open embedding model (e.g. via sentence-transformers) behind
  the same `embedder` interface.
- **Tiger Cloud:** has a free tier, but it's a cloud account. Plain local Postgres + pgvector is the
  free fallback; the html's own ADR-003 compares the two.
- **GitHub App + public webhook URL:** a real webhook needs a reachable endpoint. Replaying stored
  webhook payloads locally is probably enough for the demo. Decide at group 1 build time.

## Next

- Group 1 (ingress) matrix drafted: `FAILURE_MATRIX_01_INGRESS.md`. It has 4 TODOs for Nishant.
- Group 2 (ingestion & index) is next, after Nishant's notes on video 2 confirm or change the matrix format.
