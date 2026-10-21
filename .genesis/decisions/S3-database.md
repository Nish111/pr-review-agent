# S3 — One local store: SQLite + FTS5 + sqlite-vec

- **Date:** 2026-10-21
- **Status:** accepted
- **Phase / milestone:** 6 Memory · 14 Data · M0

## Context
Three data shapes (lecture Part II): memory (code chunks), truth (jobs, reviews, findings, human decisions), time (event trail).
The html picks Tiger Cloud (Postgres + pgvectorscale + TimescaleDB) to keep them in **one** store (its ADR-003).
Constraints: zero cost, nothing to run or administer, reuse the memory project's SQLite store code.

## Decision
**One SQLite file** holds all three shapes: relational tables for truth, an append-only events table for time,
**FTS5** (built-in full-text search) for exact-identifier search, and **`sqlite-vec`** (pip add-on) for vector search; the two result lists are merged by reciprocal rank fusion, as in the html.

## Consequences
- Positive: keeps the html's "one store, not three" argument without a cloud account; transactions span jobs + findings + events (all-or-nothing writes, which group 5 needs); the atomic claim for ingress F9 is a UNIQUE constraint.
- Negative / cost: one writer at a time, which is fine at demo scale (kickoff Q2); no live dashboards from continuous aggregates. Rollups are plain SQL views instead.
- Postgres/Tiger stays reachable behind the `store` interface (kickoff Q1: paid/scale later by config).

## Alternatives rejected
- Tiger Cloud free tier: an account and network dependency for every test run; tests stop being local and repeatable.
- Local Postgres + pgvector: a server to install and run on Windows, for no gain at this scale.
- Separate vector DB (Qdrant): exactly the split the html's ADR-003 argues against.
