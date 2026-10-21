# S1 — Free LLM for the review workload

- **Date:** 2026-10-21
- **Status:** accepted (derived from kickoff Q1 zero-cost + measured limits; Nishant may override)
- **Phase / milestone:** 5 LLM & Reasoning · M0

## Context
A full evaluation is ~20 golden PRs × (1 call at rung 2 + 4 calls at rung 3) = **~100 calls**, each ~3–5k tokens
≈ **0.4M tokens per full pass**. Free limits:
- **Groq:** 30 req/min, 8,000 tokens/min (TPM), 1,000 req/day and **200,000 tokens/day (TPD) per model**.
  The TPM matches what the memory project measured on 13 Sep 2026; the TPD is from Groq's published table as read on 16 Oct 2026 (benchlm.ai), still to be confirmed on our own console.
- **Gemini:** 20 req/day per model (measured). **OpenRouter free:** ~50 req/day (memory-project profile).
- **Ollama (local):** no quota. Nishant's laptop: 16 GB RAM, Intel Iris Xe (no NVIDIA GPU), so CPU-speed only: a small (3–7B) model at roughly 1–2 minutes per review call.

So the binding limit is **Groq's 200k tokens/day per model**, not the per-minute rate: one full pass needs about 2 Groq-model-days.

## Decision
**Groq is the main model**, using **two Groq models in rotation** (separate daily budgets, ≈ 400k tokens/day together); **Ollama runs a small local code model as the no-quota fallback** for overnight batches; **a different provider (Gemini or OpenRouter) is the checker** on small samples (maker ≠ checker).
Per-call context budget **≤ 5,000 tokens** (under the 8k TPM ceiling, which otherwise fails with 413).

## Consequences
- Positive: zero cost; a full evaluation pass fits in ~1 day of quota; the context budget forces disciplined retrieval (brief group 3).
- Negative / cost: no stability re-runs on the full set. Stability is measured instead by **3 runs on a fixed 5-PR subset**. Quota exhaustion is a real failure mode, so the budget guard + pacing from the memory project are needed from M3.
- Comparing rungs across two Groq models confounds model with rung, so **each rung's scored run uses one named model**, recorded in the trace.
- **Invariant (already in context-graph.json):** every_outbound_call_is_bounded. **Added rule for M3:** a call estimated over 5,000 tokens is trimmed by retrieval, never sent.

## Alternatives rejected
- Gemini as main: 20 req/day means ~5 days per pass.
- Local-only (Ollama): ~100 calls × 1–2 min = 2–3 hours per pass is fine overnight, but small local models review noticeably worse, and rung comparisons would mostly measure model weakness. Kept as fallback.
- Paid API: violates kickoff Q1 (stays possible later via the llm_client interface).
