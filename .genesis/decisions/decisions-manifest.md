# decisions-manifest — pr-review-agent
Generated: 2026-10-19 via KICKOFF-INTERVIEW.md. The answers were pre-filled by Claude and confirmed
by Nishant in `KICKOFF_ANSWERS_DRAFT.md`, which has the full reasoning and consequences. This file is the input to G0.

## Trade-off ranking
1. cost: zero cost / free tiers only, **but** every paid-vs-free choice sits behind an interface so a paid tier can be added later by config
2. reliability: the brief grades failure handling
3. maintainability
4. speed: only the webhook acknowledgement is time-critical

## Scale
Launch: 1–2 demo repos, a few PRs/day, golden set of ~20–50 PRs
12 months: same. Cohort deliverable + portfolio piece, no user base.

## Project type
production-shaped prototype: production habits (failure matrices, tests, traces), prototype scale

## Performance constraints (non-negotiable)
- webhook acknowledged in < 10 s (GitHub marks the delivery failed otherwise and does **not** retry; see the ingress matrix F11)
- full review within ~5 min (soft); local test suite under 2 min

## UX / brand constraints
Review comments read like a careful senior reviewer: short, specific, file + line + evidence on every finding, no padding.
Status messages never promise a time ("review delayed, will update here once done"), and one status comment is edited in place.
Dashboards: plain and dense; looks don't matter.

## Failure behaviour
Degrade to slower-but-correct, never fast-but-wrong. Nothing is silently dropped (write-ahead log, dead-letter queue, redelivery job, sweeper).

## Integration points
- GitHub: webhooks in (`pull_request`, `issue_comment` for `/review`); REST API for diffs, files and comments; reviews and commit statuses posted back
- free-tier LLM provider(s): reuse the provider layer from `05-Memory-Intelligence-System/incident_memory/spikes/extraction.py`
- local database + vector search (choice is spike S3)
- local Redis or a stand-in for the queue

## Auth requirements
- only repo members (OWNER / MEMBER / COLLABORATOR) can trigger `/review`
- only a human approves a review held in the approval queue
- the bot never approves or merges a PR; it only comments

## Compliance constraints
- no secrets or tokens in logs
- private-repo code is never sent to a provider that trains on inputs
- golden set uses only public repos or Nishant's own

## Primary failure mode (the honest one)
The evaluation never gets built: the golden PR set slips to the end and the agent ships with no proof it beats the baseline.
Nishant: "if it fails it should fail early." → golden set + first baseline-vs-upgraded run go **early** in the milestone order.

## Quality bar ("embarrassed to ship if...")
...it posts a confident, wrong finding (a false security alarm, or a citation of code it never read).
→ **precision is the priority metric**; recall is tracked but secondary.

## Known unknowns → research spikes needed (before M1)
- S1: which free LLM gives usable review quality within free-tier limits
- S2: which free embedding model replaces the html's paid `text-embedding-3-large`
- S3: Tiger Cloud free tier vs local Postgres + pgvector
- S4: golden PR source: own repos / a public OSS repo with known-bad merges / synthetic (handoff D2)
- S5: what the instructor builds in videos 6–10, i.e. the baseline to improve on
Nishant: "better to start, go slowly and make a real difference than do rework."

## Assumptions never stated aloud (agent-inferred from answers above)
- A1: provider, embedding and database choices are hidden behind interfaces, so cost can change without a redesign
- A2: the bot comments only; humans keep all merge/approve power, so an autonomy level above "human handles exceptions" is out of scope
- A3: the demo can run on replayed webhooks; a live GitHub App is needed only for the final recording (ingress matrix, open TODO)
- A4: sequencing follows the sprint plan: the outreach week (4–10 Nov) is not displaced by this project
- A5: free-tier rate limits are the real capacity ceiling, so the budget guard and pacing from the memory project are needed from M1
- **S6 (7 Nov 2026):** default configuration: four specialists, no code search, calibrated threshold 0.84 (`decisions/S6-default-configuration.md`).
