# M9 live demo log

## A · `Nish111/notes-svc-demo`, PR #1 "Add note search by keyword" (S01), 9 Nov 2026

Source: `.pr_review/store.db` (events table, `review.done`) and the bot's console output in `Temp10.md`.

| Step | Result |
|---|---|
| First start | failed: the private-key path in `GITHUB_APP_KEY_PATH` didn't exist; fixed by Nishant, restarted |
| Webhook `pull_request` (opened) | signature verified, 202 accepted, one job `Nish111/notes-svc-demo#1@5ddca95` |
| Specialists | 4 of 4 completed, 0 findings dropped, 0 errors, 1 exact duplicate merged |
| Route | **1 comment posted, 0 queued** (threshold 0.84, decision S6); not partial |
| Follow-up webhook `issue_comment` (the bot's own comment) | 200, ignored (not a `/review` command), as designed (ingress F17) |
| Job | done after 1 attempt |

**Measured tokens (first run with the provider's own counts, matrix 06 E-F1):**

| Specialist | input | output | of which reasoning |
|---|---|---|---|
| security | 1,423 | 448 | 182 |
| quality | 1,431 | 478 | 175 |
| tests | 1,416 | 579 | 300 |
| docs | 1,430 | 326 | 309 |
| **total** | **5,700** | **1,831** | 966 |

- Cost if paid: 5,700 × $0.15/M + 1,831 × $0.60/M ≈ **$0.002 for this review** (prices as in `reports/report.html`).
- **Finding:** our estimate for these prompts was about 1,140 input tokens each (characters ÷ 4, the rung 3 cache); the measured count is
  about 1,425, so the estimate **under**-counts by roughly 25% on code. The 5,000-token per-call cap is therefore about 6,250 real
  tokens, still under Groq's 8,000 per minute, but the "pessimistic" label on the estimate (single.py) was wrong. One PR, four calls:
  a small sample.
- Reasoning tokens were 966 of 1,831 output tokens (53%): the hidden cost matrix 06 warned about is real and large.

**The posted comment (copied from the PR page by Nishant, 9 Nov):**

PR review bot · automated comments only; it never approves or merges.

high · Search query interpolates user input directly into SQL, allowing injection and quoting errors (notes_svc/notes.py:31-34)
The function builds the SQL statement with f-strings that embed user_id and keyword directly (lines 32-33). This bypasses SQLite parameter binding and permits malicious keyword values (e.g., containing a single quote or SQL syntax) to alter the query, causing incorrect results, runtime errors, or data leakage.
Suggestion: Rewrite the query to use parameter placeholders and pass the values separately, e.g.,
rows = conn.execute(
    "SELECT id, title, body FROM notes WHERE user_id = ? AND (title LIKE ? OR body LIKE ?)",
    (user_id, f"%{keyword}%", f"%{keyword}%")
).fetchall()

## C · `Nish111/ScalerBeginner`, PR #2 "Add score helpers" (bot_demo/scores.py, 2 planted bugs), 9 Nov 2026

| Step | Result |
|---|---|
| App access added | webhook `installation_repositories`, ignored as designed |
| Webhook `pull_request` (opened) | 202 accepted, one job `Nish111/ScalerBeginner#2@486be17` |
| Specialists | 4 of 4 completed, 0 dropped, 0 errors, 0 exact duplicates |
| Route | **1 comment posted, 0 queued** |

Measured tokens: 4,468 in / 2,479 out (1,176 reasoning) ≈ $0.002 if paid.

**Claude's prediction was wrong:** it predicted most comments would go to the queue (uncalibrated code); everything posted.
**Open question, to check against the comment's text:** all findings fell into **one** group. The file is new (27 lines), so a single
finding that cites a wide range (e.g. "no tests for this file", lines 1-27) overlaps every other finding and pulls them into one
group (matrix 05, G1 groups by overlapping lines). Then only the lead is the comment's headline and the other bugs become
supporting lines. If the comment shows that, it's a real aggregator weakness on new files, to note in the write-up.

**The posted comment (copied from the PR page by Nishant, 9 Nov):**

PR review bot · automated comments only; it never approves or merges.

high · average() raises ZeroDivisionError on empty input list (bot_demo/scores.py:6-6)
The function returns sum(scores) / len(scores) without checking for len(scores) == 0, so calling average([]) will cause a division by zero exception.
Suggestion: Add a guard for empty lists, e.g., return 0 or raise a descriptive ValueError.
quality reviewer + docs, quality, tests · calibrated score 0.88

**Reading C's comment (Claude, 9 Nov):** the open question is answered: **yes**. All four reviewers' findings became one comment.
Its headline is the empty-list crash (`average([])`, right). The other findings appear only as names ("+ docs, quality, tests").
A second **quality** finding is among them; it is probably the grade-90 boundary bug, but the comment doesn't show its text, so
**the second planted bug is invisible to the developer**. Two weaknesses, both in the aggregator, not in the reviewers:
1. **Grouping:** on a new file, a finding that cites the whole file overlaps every other finding and glues separate bugs into one group (matrix 05, G1).
2. **Rendering:** supporting findings are shown only as reviewer names, not their one-line summaries (matrix 05, G2 promised "supporting lines").

Both are recorded here as found in the live demo. A fix would change rung 4's grouping, so it would be reported as a post-hoc
re-run next to the official rung 4 numbers, never in place of them.
