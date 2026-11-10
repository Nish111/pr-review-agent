# Architecture decision records

- [ADR-0001](ADR-0001.md) · Build evaluation first, then the system
- [ADR-0002](ADR-0002.md) · Free LLM: openai/gpt-oss-120b on Groq
- [ADR-0003](ADR-0003.md) · Local embeddings: bge-small (jina planned)
- [ADR-0004](ADR-0004.md) · One SQLite file instead of Redis + Tiger Cloud
- [ADR-0005](ADR-0005.md) · Golden set: 14 seeded + 5 real PRs
- [ADR-0006](ADR-0006.md) · The baseline is the lecture design, rebuilt where needed
- [ADR-0007](ADR-0007.md) · Default: four specialists, no code search, calibrated threshold 0.84
- [ADR-0008](ADR-0008.md) · One process, thread fan-out, shared token bucket (no LangGraph)
- [ADR-0009](ADR-0009.md) · Comments only; humans approve; the bot never approves or merges
- [ADR-0010](ADR-0010.md) · Hand check is the official right-reason measure; the AI judge is secondary

Each ADR points to the fuller decision note in `.genesis/decisions/` where one exists.
