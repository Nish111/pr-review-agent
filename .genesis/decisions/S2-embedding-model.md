# S2 — Free embedding model for code search

- **Date:** 2026-10-21
- **Status:** accepted (confirm it installs and runs at the start of M5)
- **Phase / milestone:** 6 Memory · M0

## Context
Hybrid retrieval needs an embedding model for "similar code". The html uses OpenAI `text-embedding-3-large` (paid).
Laptop: 16 GB RAM, no NVIDIA GPU, so a small model on CPU is fine; the corpus is 1–2 demo repos (thousands of chunks, not millions).

## Decision
Use a **local, code-trained embedding model via `sentence-transformers`**: first choice
`jinaai/jina-embeddings-v2-base-code` (code-specific, 768 dimensions, Apache-2.0); fallback `BAAI/bge-small-en-v1.5`
(384 dimensions, smaller and faster) if the first is too slow on CPU. The choice sits behind the `embedder` interface.

## Consequences
- Positive: no quota, no network, no cost; indexing is repeatable (same input gives the same vectors).
- Negative / cost: a ~300 MB one-time model download; CPU indexing of a mid-size repo takes minutes, not seconds, so the incremental refresh (re-embed only changed files) matters.
- Exact-identifier search does **not** depend on this model (it's keyword search, S3), so a weak embedding hurts only the "similar code" half.

## Alternatives rejected
- OpenAI / Voyage code embeddings: paid.
- Embeddings through a free LLM API: spends the same daily quota S1 needs for reviews.
