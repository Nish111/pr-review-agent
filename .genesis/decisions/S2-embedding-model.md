# S2 — Free embedding model for code search

- **Date:** 2026-10-21
- **Status:** accepted, amended 26 Oct 2026 after the M5 spike: **bge-small is the model in use**
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

## Amendment, 26 Oct 2026: spike result (eval/spikes/s2_embed_check.py on Nishant's laptop)
- Python 3.13.3, SQLite 3.49.1: FTS5 ok, sqlite-vec 0.1.9 ok.
- `BAAI/bge-small-en-v1.5`: 384 dims, 0.115 s per chunk on CPU (about 2-3 min for click's 1,284 chunks); similar vs unrelated code 0.77 vs 0.54.
- `jinaai/jina-embeddings-v2-base-code`: **fails to load** with transformers 5.20 (its downloaded code imports
  `find_pruneable_heads_and_indices`, which transformers 5 removed). Running it needs older library versions in a separate environment.
- Nishant chose A (allow jina's remote code), but A can't run as installed, so **bge-small is used** (Claude's call, open to his objection).
  jina is reconsidered only if M6 shows the vector lane improves reviews.
- Each index records the exact model version it was built with (`name@commit`, read from the local Hugging Face cache), so an updated model is refused, not mixed (matrix 02, I8).
- Side effect, disclosed: the install went into his user-wide Python and upgraded `click` 8.1.8 → 8.5.0 and `anyio`. Next time a heavy dependency is added, a project venv comes first.
