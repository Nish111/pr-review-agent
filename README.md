# PR Review Agent

## What it is, in one paragraph

When someone opens a pull request (PR) on GitHub, this bot reads the change and looks for bugs: security holes, logic
mistakes, missing tests, wrong docs. It **posts a comment only when it is confident the bug is real**. Anything it is unsure
about goes to a person first, who approves or rejects it. It never approves or merges a PR; that stays with people.

**Example (a real run, `eval/M9_DEMO_LOG.md`):** a PR added a search endpoint that built its SQL query by pasting the user's
text into the query string. The bot commented on that line: *this is SQL injection, use a `?`
placeholder instead*, and showed the fixed code.

## How it works, step by step

```
 PR opened on GitHub
        │  GitHub sends a notification (a "webhook")
        ▼
 1. Receive   — check the notification is really from GitHub, save it, put a review job in a queue
        ▼
 2. Read      — fetch the PR's changed lines (the "diff")
        ▼
 3. Review    — four AI reviewers each look for one kind of problem:
                security · code quality · tests · docs
        ▼
 4. Combine   — merge findings that point at the same lines, give each a confidence score
        ▼
 5. Decide    — score ≥ 0.84, not critical, review complete  →  post the comment on the PR
                otherwise                                    →  put it in the approval queue for a person
        ▼
 6. Record    — save every step (what was read, what the AI was asked, what it answered, cost, time,
                and what the person decided) so any comment can be traced back later
```

Why the 0.84 cut-off: it was chosen from test results so that the comments that do get posted are almost always right
(on the test set, 8 out of 8). Fewer comments, but people can trust them.

## Does it work? How we measured

We built a small test app and **14 practice PRs**: 10 with a bug planted on purpose, 4 with no bug. We knew the answers in
advance, so we could score each version of the bot. We wrote down the scoring rules *before* each run, so results could not be
tuned after the fact. A person checked each match to confirm the bot named the right bug, not just the right line.

We built the bot in four steps ("rungs"), each one measured against the same 14 PRs:

| Version | What it does | Planted bugs found | Comments that were right |
|---|---|---|---|
| 1 | standard code-checking rules, no AI | 2 of 10 | 22% |
| 2 | one AI reviewer | 5 of 10 | 50% |
| 3 | four specialist AI reviewers | 9 of 10 | 55% |
| **4 (final)** | **four reviewers + combine + confidence cut-off** | **posts fewer, sends the rest to a person** | **8 of 8 posted were right** |

Each version is better than the one before it. Version 4 trades "find everything" for "only say what is right".
Full numbers: `eval/findings_rung1.md` … `eval/findings_rung4.md`.

## Known weak spots (honest list)

- The test set is small (14 PRs), so the numbers are a first estimate, not a guarantee.
- When one PR has two bugs close together, the combine step can merge them into one comment and the second one gets hidden (seen in a live demo).
- On 5 real PRs from an open-source project (click), the final version posted nothing and sent everything to a person.
- Not built yet: alerting, tracking quality over time, a test for PRs that try to trick the AI.

## Try it

Python 3.10+, in Git Bash (Windows) or any shell, from this folder:

```
python -m venv .venv
source .venv/Scripts/activate            # Linux/macOS: source .venv/bin/activate
python -m pip install cryptography pytest ruff
python -m pytest -q                      # runs the tests
```

Put `PYTHONPATH=src` before each command:

| Command | What you see | Needs |
|---|---|---|
| `python -m pr_review trace S01` | one review step by step: what the bot read, asked, answered and decided | nothing |
| `python -m pr_review report` | `reports/report.html`: quality, cost, speed, every human decision | nothing |
| `python -m pr_review rung4 --on 3n` | re-scores the final version on the 14 PRs | nothing |
| `python -m pr_review serve` | the live bot on a real GitHub repo | a GitHub App and a free AI key (`GROQ_API_KEY`); steps in `M9_START.md` |
| `python -m pr_review queue` | the approval queue; `approve <id>` posts the comment | the live bot set up |

## For reviewers: where each brief deliverable is

| Brief deliverable | Where |
|---|---|
| Genesis-managed repository | `.genesis/` (plan, milestones, decisions) |
| Architecture and decisions (ADRs) | `docs/ARCHITECTURE.md`, `docs/adr/` |
| Failure matrices: what can go wrong in each part and how it is handled | `FAILURE_MATRIX_01_INGRESS.md` … `FAILURE_MATRIX_07_EVALUATION.md` |
| Working PR → review demo | `serve` above, `eval/M9_DEMO_LOG.md` |
| Before-vs-after evaluation | `eval/PREREG_RUNG*.md` (rules written before each run), `eval/findings_rung*.md` |
| Traces | `trace` and `report` above |
