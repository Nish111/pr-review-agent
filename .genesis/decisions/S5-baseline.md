# S5 — What the "supplied baseline" is

- **Date:** 2026-10-21
- **Status:** provisional; final after Nishant's notes on videos 6–10
- **Phase / milestone:** 1 Architecture · M0

## Context
Brief §1: "start from the supplied baseline… preserve the baseline, then show the improvement story."
No baseline code was supplied: the course Drive folder holds only 10 lecture videos (Nishant's check, `10-PR-Review-Agent/STEP3_FIND_BASELINE.md`, 19 Oct 2026).
The design document `Antern\Session15-16\pr-review-agent.html` gives the architecture, a 23-module map and ADR-001/002/003, with no code.
Nishant's video-1 notes (`PR Agent Doc.docx`) call the roadmap "the baseline, what u build is on top of this".

## Decision (provisional)
The baseline is **the html design plus whatever the instructor builds in videos 6–10**. Our measured "before" is
**rung 1 (rule-based checks) and rung 2 (single LLM reviewer)**, which we build ourselves (M2, M3), as the brief's ladder starts there.

## Consequences
- If videos 6–10 show code being built that is shared anywhere, this note is updated and that code becomes the "before" for the ingress and specialist groups.
- If not, the before/after story rests on our own rungs 1–2, which the brief's improvement ladder allows.

## Open
- [ ] Nishant's notes on videos 6–10 (S5 closes when these exist).
