# Wiki Index — pr-review-agent

The project knowledge base. Same schema as the agentic-swe-kit wiki: concept pages in `concepts/`,
each with frontmatter and ≥2 `[[wikilinks]]`. The L3 RESEARCH loop writes here; G0 reads here first.

> **Read this file before any milestone (G0 step 1).** Pick candidate pages by name-matching the
> milestone's nouns, then drill in. The wiki is what prevents rebuilding work that already exists.

## Entities (the things this system has)
<!-- - [[concepts/<Entity>]] — one-line summary -->

## Concepts (how it works)
<!-- - [[concepts/<Concept>]] — one-line summary -->

## Sources (research distilled by L3)
<!-- - [[concepts/<source-slug>]] — one-line summary | filed <date> -->

## Seeded from agentic-swe-kit
Relevant global concept pages for this project's phases (pointers only — read on demand):
- `$AGENTIC_SWE_WIKI_ROOT/clean-architecture/concepts/` — when setting module boundaries (contracts at the centre, adapters behind interfaces).
- `$AGENTIC_SWE_WIKI_ROOT/distributed-systems/concepts/` — when building ingress & queue: idempotency, atomic claims, retries, dead-letter, backpressure (ingress matrix).
- `$AGENTIC_SWE_WIKI_ROOT/designing-data-intensive-applications/concepts/` — when designing the store, the incremental index refresh and the event trail.
- `$AGENTIC_SWE_WIKI_ROOT/llmops-ai-agents/concepts/` — when designing specialists, structured Finding output, prompt versioning, evaluation and confidence calibration.
- `$AGENTIC_SWE_WIKI_ROOT/security-engineering/concepts/` — when handling the trust boundary: webhook signatures, prompt injection, fork PRs, secrets in logs.

Project sources (not in the kit, read on demand):
- `../FAILURE_MATRIX_01_INGRESS.md` — group 1 failure matrix (v3), 17 failure modes, 16 tests.
- `../COMPONENT_LIST.md` — crosswalk: lecture's 5 components ↔ brief's 7 groups ↔ html's 23 modules.
- `D:\Nishant\Learnings_NewLaptop\Antern\Session15-16\pr-review-agent.html` — the supplied baseline design (outside the repo).
