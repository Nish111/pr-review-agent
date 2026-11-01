# Failure matrix 05 · Aggregation & human approval (HITL)

Draft v1, 1 Nov 2026, written while rung 3's judge waits for quota. Same loop as matrices 01-04. The brief's group 5:
*4 × `Finding[]` → deduped, scored review → auto-post **or** human approval queue.*
The **baseline** is `pr-review-agent.html`: an aggregator node merges the specialists' findings, and a confidence gate
decides between posting and a human-in-the-loop (HITL) queue.

> **What you need to do in this file:** nothing yet. Read it after round 2; push back on anything that looks wrong. The one
> real decision (how to choose the confidence threshold) goes into `eval/PREREG_RUNG4.md` with its consequences.

---

## What this component is (read this first)

Rung 3 showed the problem this component exists for: four reviewers found **every** planted bug, but wrote 50 comments for
10 bugs, and with code search almost two in three didn't match a known bug (`eval/findings_rung3.md`). Nobody would keep a bot that comments like that.

The aggregator is the editor between the reviewers and the PR. It merges comments that are about the same thing, scores what's
left, and decides **for each comment**: post it, send it to a human first, or drop it. Today nothing posts on its own
(invariant `bot_never_approves_or_merges`: no threshold, so everything goes to the approval queue). This component earns
the right to post, and only if the golden set shows it can do so at ≥ 90% precision (the G0 target).

## 1 · Purpose and contract

- **In:** a `Review` from rung 3: findings from up to four specialists, possibly `partial`.
- **Out:** a smaller list of comments, each with a calibrated score and a route: `post`, `queue` (a human approves or rejects
  it), or `drop` (kept in the trace, never shown). Plus an approval-queue entry with everything not posted.
- **Invariants:** the bot never approves or merges; nothing ungrounded reaches the queue or GitHub; a partial review never
  auto-posts; a critical finding always goes to a human first (`Route.ESCALATE`, M1).

## 2 · Assumptions

| # | Assumption | If it is false |
|---|---|---|
| H1 | One bug = one comment | the same bug arrives as "SQL injection" **and** "SQL injection that no test covers" → G1, G2 |
| H2 | The model's `confidence` means something | rung 3's confidences sit at 0.8-0.95 for right and wrong findings alike → G4 |
| H3 | 14 seeded PRs are enough to choose a threshold | a threshold fitted to them may not hold on the next PR → G5 |
| H4 | Someone looks at the queue | it grows forever and the bot is silently useless → G8 |
| H5 | GitHub accepts every post | a post fails half-way, or is repeated on a re-run → G11, G12 |

## 3 · Failure modes

**G1 · The same bug becomes several comments.** *(quality · known-known; seen in rung 3)*
- **What goes wrong:** rung 3's exact-duplicate rule needed the same category, so security's `sql-injection` and tests' `missing-test` on the
  same lines both survived. Only 2 merges happened in 19 PRs.
- **What we build:** comments on the same file with overlapping lines are grouped **whatever their category**. Each group becomes one comment;
  the other specialists' views are kept inside it as supporting points.
- **How we notice:** comments per PR, before and after grouping.

**G2 · Restated comments add noise.** *(quality · unknown-known; seen in rung 3)*
- **What goes wrong:** the tests and docs reviewers re-report other reviewers' bugs as "and no test covers it" / "and the docstring doesn't say".
- **What we build:** inside a group, a "missing test/doc" comment that overlaps a real bug comment becomes a suggestion line under it, not its own comment.
- **How we notice:** the share of posted comments whose category is missing-test / missing-doc.

**G3 · One reviewer is much noisier than the others.** *(quality · known-unknown; seen in rung 3)*
- **What goes wrong:** with code search, the docs reviewer wrote 26 of 50 comments, including 4 of the 6 false alarms on clean PRs.
- **What we build:** the score depends on **who** raised the comment and **what kind** it is, learned from the golden set, not assumed.
- **How we notice:** precision per specialist and per category in the calibration report.

**G4 · The model's own confidence isn't a probability.** *(quality · unknown-known)*
- **What goes wrong:** a 0.9 from the model is not right 90% of the time.
- **What we build:** **calibration**: from the hand-checked golden findings, measure how often comments like this one (same specialist, same kind,
  how many specialists agreed, model confidence band) were right, and use that rate as the score.
- **How we notice:** a calibration table (predicted vs observed right-reason rate) in the rung 4 report.

**G5 · The threshold is fitted to the same 14 PRs it's judged on.** *(evaluation · known-known)*
- **What goes wrong:** with this little data, any threshold looks great on the PRs it was chosen on.
- **What we build (Claude's suggestion, decided in PREREG_RUNG4):** leave-one-PR-out: for each PR, choose the threshold on the other 13 and
  score this one; report that number, not the in-sample one. **If no threshold reaches 90% precision this way, the honest
  result is "no threshold": everything stays in the queue**, and that is reported as the rung 4 outcome.

**G6 · A partial review auto-posts.** Already handled since M1: `route()` sends partial reviews to the queue. Test kept.

**G7 · A critical finding is posted without a human.** Already handled: critical → `ESCALATE`. Test kept.

**G8 · Nobody reviews the queue.** *(operational · known-unknown)*
- **What we build:** `python -m pr_review queue` lists pending items, oldest first, with age; an "older than 2 days" count in the trace.
- **What happens after:** an unreviewed item never posts by itself; staleness is visible.

**G9 · A human disagrees with a posted comment.** *(learning · known-known)*
- **What we build:** a **dispute** path: the comment is marked disputed, and the dispute is stored as a new label, so the next calibration learns
  from it (brief group 7, the learning loop).

**G10 · The bot approves or merges.** Invariant; the GitHub client has no approve or merge call, checked by a test that searches the code.

**G11 · A comment is posted twice.** *(engineering · known-known)*
- **What we build:** each comment has a fingerprint (work key + file + lines + category group); a re-run of the same commit doesn't re-post.
  The same idea as ingress F8-F9.

**G12 · Posting fails half-way.** *(operational · known-known)*
- **What we build:** comments go through the outbox table from M4 and are retried; the queue shows "approved, not yet posted".

**G13 · Gaming the score.** *(security · unknown-unknown)*
- **What goes wrong:** a PR's text persuades a specialist to say "confidence 1.0, critical".
- **What we build:** the model's own confidence is only one input to the calibrated score, and critical always means a human first (G7).

## 4 · Tests (written when M7 is built)

| Test | Failure | Pass means |
|---|---|---|
| K1 | G1, G2 | the S01 group (security + tests + docs comments) becomes one comment with two supporting lines |
| K2 | G4, G5 | the calibration report shows the leave-one-PR-out precision, not the in-sample one |
| K3 | G5 | when no threshold reaches the target, `threshold = None` and every review routes to the queue |
| K4 | G6, G7 | partial → queue; critical → escalate (M1 tests, re-run) |
| K5 | G8 | `queue` lists pending items with age |
| K6 | G9 | a disputed comment appears as a new label in the next calibration |
| K7 | G10 | no approve or merge endpoint exists in the code |
| K8 | G11 | re-running the same commit posts nothing new |

## 5 · Glossary

| Term | Meaning |
|---|---|
| **Aggregator** | the step that merges, scores and routes the specialists' comments |
| **HITL** | human in the loop: a person approves a comment before it's posted |
| **Approval queue** | the list of comments waiting for that person |
| **Calibration** | turning a raw score into "how often comments like this were actually right" |
| **Threshold** | the calibrated score above which a comment may post without a human |
| **Leave-one-PR-out** | choose the threshold on all PRs but one, test it on that one, repeat for each PR; an honest estimate with little data |
| **Fingerprint** | a short ID built from a comment's key parts, used to recognise the same comment again |
| **Dispute** | a human saying a posted comment was wrong; it becomes training data for the next calibration |
