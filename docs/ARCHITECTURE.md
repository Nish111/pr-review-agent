# PR Review Agent · Architecture (as built, 9 Nov 2026)

A selective, grounded, failure-aware pull-request reviewer, built with Genesis for the AI Sprint W8 brief. It does the mechanical
part of review consistently, posts only findings it is calibrated to trust, and routes everything uncertain, critical or partial to
a human. **It never approves or merges.**

Decisions are in `docs/adr/` (ADR-0001 … ADR-0010). Failure analysis is in `FAILURE_MATRIX_01` … `07`. Numbers are in `eval/findings_rung1-4.md`
and `reports/report.html`. The live demo is in `eval/M9_DEMO_LOG.md`.

## 1 · The path of one pull request

```
GitHub ──webhook──▶ smee relay ──▶ webhook_receiver ──▶ job_queue ──▶ live/worker
 (PR opened)                       HMAC check, filter,   SQLite jobs,     │
                                   dedupe, inbox (M4)    retries, DLQ     ▼
                                                                  github_client: PR, diff, changed files (head)
                                                                          │
                                                   orchestrator: 4 specialists in parallel (M6)
                                                   security · quality · tests · docs, one shared
                                                   8k tokens/min budget + 20k per-review BudgetGuard
                                                   [retrieval (M5) exists, off by default: ADR-0007]
                                                                          │  Finding[] (grounded only)
                                                                          ▼
                                                   aggregator (M7): group by lines, fold test/doc
                                                   restatements, calibrated score per comment
                                                                          │
                                        score ≥ 0.84, not partial, not critical │ everything else
                                                    ▼                           ▼
                                        one PR comment (bot)            approval queue (human)
                                                    │                           │ approve / reject / dispute
                                                    └──────────▶ events + labels ◀┘ ──▶ recalibrate (report only)
```

## 2 · Components and where they live

| Brief group | Component | Code | Store tables |
|---|---|---|---|
| 1 Ingress & queue | webhook receiver, job queue, sweeper, inbox | `webhook_receiver/`, `job_queue/` | deliveries, jobs, dead_letters, commands, pushes, outbox, events |
| 2 Ingestion & index | AST chunker, walker, incremental index | `ingestion/`, `embedder/` | index_files, chunks, chunks_fts, chunks_vec_repo, vec_cache |
| 3 Retrieval & grounding | hybrid search, token budget, stale/no-index modes | `retrieval/` | (reads the index) |
| 4 Workflow & specialists | four prompts, orchestrator, token bucket, BudgetGuard | `orchestrator/`, `specialists/`, `prompts/rung3_*.txt` | (per-call cache files in eval) |
| 5 Aggregation & HITL | grouping, calibration, threshold, approval queue | `aggregator/`, `hitl/`, `config.py` | approvals, calibration_labels, posted |
| 6 Data, proof & economics | events, trace, report, usage capture | `trace/`, `reports/`, `llm_client/` | events |
| 7 Evaluation & learning | golden set, scorers, right-reason check, gate, recalibration | `evaluation/`, `golden/`, `eval/` | — |
| Shared | contracts (Finding, Review, Job, route) | `contracts/` | — |

Everything runs in **one Python process with one SQLite file** (ADR-0004, ADR-0008). The only required dependency outside the
standard library is `cryptography`, for the GitHub App key. `sentence-transformers` and `sqlite-vec` are only needed when code search is switched on.

## 3 · What changed from the baseline (`pr-review-agent.html`)

| Baseline (lecture design) | As built | Why (evidence) |
|---|---|---|
| Redis + ARQ queue, Tiger Cloud (Postgres, pgvectorscale, Timescale) | one SQLite file: jobs, index, events, approvals | zero cost and nothing to run; atomic claim = UNIQUE constraint (ADR-0004); ingress T8: 50 concurrent copies → 1 job, the lecture design → 31-50 |
| check-then-enqueue dedupe | one transaction per delivery + work-key claim + inbox | `FAILURE_MATRIX_01` §6: T7, T8, T10, T12 before/after |
| OpenAI embeddings, hybrid search always on | local bge-small; hybrid search built but **off by default** | rung 3/4: search added 1 bug for a precision drop 0.55 → 0.30 (ADR-0003, ADR-0007) |
| LangGraph parallel fan-out | thread pool + shared token bucket | free tier is 8k tokens/min; plain fan-out sends ~12k at once (matrix 04, W2; ADR-0008) |
| confidence gate on model confidence | calibrated score from hand-checked golden labels, chosen leave-one-PR-out | the model's confidence sat at 0.8-0.95 for right and wrong alike (matrix 05, G4; ADR-0007) |
| LLM-as-judge for evaluation | hand check official, judge reported alongside | judge's independent agreement 6/9 and 18/27 (ADR-0010) |

## 4 · Invariants (checked by tests)

| Invariant | Enforced by | Test |
|---|---|---|
| every posted finding is grounded | `Finding.is_grounded` against shown spans | `tests/test_contracts.py`, `test_rung3.py` (Z5) |
| one live job per work key | UNIQUE work_key + one transaction per delivery | `tests/ingress` T7, T8 |
| the bot never approves or merges | no such call in `github_client`; comments only | `tests/test_rung4.py` (K7) |
| every outbound call is bounded | timeouts, 5k tokens per call, token bucket, BudgetGuard | `test_rung3.py` (Z2), `test_trace_report.py` (V2) |
| no secrets in logs or reports | allow-listed fields only | `tests/ingress` (F15), `test_trace_report.py` (V5) |

## 5 · Traceability: failure mode → decision → implementation → test → evidence (brief §4 "done")

| Group | Example failure mode | Decision | Implementation | Test | Observable evidence |
|---|---|---|---|---|---|
| 1 | same delivery 50× at once | ADR-0004 | `receiver.py` `ingest` (BEGIN IMMEDIATE) | ingress T8 | `eval/results/ingress_compare.json`: 1 job vs 31-50 |
| 1 | database down | matrix 01 F12 | inbox.jsonl + `drain_inbox` | ingress T10 | 20/20 kept vs 0/20 |
| 2 | ghost chunks after shrink/delete | matrix 02 I6 | `index.py` replace-whole-file | `tests/index` X2, X3 | `index_compare.json`: 0 vs 7 |
| 2 | one-line edit re-embeds all | matrix 02 I7 | vector cache by chunk-text hash | X4 | 2 vs 13 embeddings |
| 3 | exact names missed by stemming | matrix 03 R1 | definition lookup + whole-name FTS | Y1 | 891/891 vs 813/891 (by construction; caveats in matrix 03 §5) |
| 3 | another repo's chunks leak in | matrix 03 R12 | one index file per repo | `test_vector_lane_ignores_other_repos` | found mid-run, disclosed in `PREREG_RUNG3.md` |
| 4 | per-minute limit with 4 parallel calls | ADR-0008 | `TokenBucket` | Z2 | 144/144 rung 3 calls answered; 16 needed one transport retry, all in the no-search arm, which on 29 Oct ran **at the same time** as the search arm with its own budget (two buckets, one Groq limit) |
| 4 | one specialist fails | matrix 04 W1 | partial review → queue | Z1 | R1 network failure recorded as partial, re-asked |
| 5 | same bug, four comments | matrix 05 G1-G2 | grouping + folding | K1 | 50 → 33 comments (rung 4) |
| 5 | uncalibrated confidence | ADR-0007 | calibration table, leave-one-PR-out | K2, K3 | `rung4n.json`: 8/8 posted right; `rung4.json`: no threshold |
| 6 | cost unknown | matrix 06 E-F1, E-F2 | usage capture, report | V1, V6 | `M9_DEMO_LOG.md`: 5,700 in / 1,831 out measured |
| 6 | trace can't show the prompt | matrix 06 E-F5 | rebuild + fingerprint check | V4 | `trace S01`: 4/4 prompts match |
| 7 | a change makes reviews worse | matrix 07 L6 | `gate` | Q1-Q3 | gate result on a candidate run |
| 7 | judge unreliable | ADR-0010 | hand check official | — | `findings_rung2.md` §3, `findings_rung3.md` §5 |

## 6 · Known limitations (stated, not hidden)

- **Small evidence:** 14 seeded + 5 real PRs; "8 of 8 posted right" has a 95% range of 0.68-1.00.
- **Grouping hides bugs on new files** (live demo C): a whole-file comment glues separate bugs into one, and supporting findings show only as names (`M9_DEMO_LOG.md`).
- **Not measured:** run-to-run stability (matrix 07, L9), model drift, latency/cost **alerts** (the report shows them; nothing alerts).
- **Not built:** a planted prompt-injection PR in the golden set; tool permissions/isolation (the specialists have no tools, so there is nothing to isolate yet).
- **Real PRs:** at the default setting the bot posts nothing on the click PRs; everything goes to the queue.
- **Token estimates** under-count code by about 25% (measured in M9); the per-call cap still fits Groq's limit.
