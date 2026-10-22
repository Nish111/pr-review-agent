# M1 · The golden set: 14 seeded PRs + 6 real click PRs

Written 21 Oct 2026. Builds on `.genesis/decisions/S4-golden-pr-source.md` and your pick, `pallets/click` (`M1_REAL_REPO_PICK.md`).

## What we're doing and why

Every version of the reviewer (rungs 1–4) gets scored on the same ~20 PRs, so this set is the yardstick
for the whole project. Most of it (14 PRs) we **write ourselves** in a small demo app, with a problem
**planted on purpose** in 10 of them and **nothing wrong** in 4. Because we planted the problems, the right answer is known exactly.

The plan below is **what each PR will contain**. Nothing is built yet. The expensive part
(writing the app and 14 diffs) only starts after you've checked the plan, because a bad plan means rewriting PRs.

## The demo app (what the 14 PRs change)

**`notes-svc`**: a small Python service, standard library only, about 400 lines: users log in with a token, save
notes to SQLite, search them, and export them to a file. It's chosen so that every specialist has realistic
things to find: a database (injection), tokens (timing attacks), file paths (traversal), a command-line tool (docs).
It becomes its own public GitHub repo later, which is also the live demo target for M9.

## The 14 seeded PRs (v2, revised after your review)

| ID | PR title (as a developer would write it) | Planted problem | Specialist that should catch it | Severity |
|---|---|---|---|---|
| S01 | Add note search by keyword | search query built with an f-string → **SQL injection** | security | critical |
| S02 | Speed up token check | token compared with `==` → **timing attack** (same idea as ingress F1) | security | high |
| S03 | Let users name their export file | file name used as-is → **path traversal** (`../../etc/x`) | security | high |
| S04 | Save tags together with the note | note and its tags written in **two separate database writes with no transaction**: if the second fails, the note is saved without its tags (partial write) | quality | high |
| S05 | Show tags in the note list | tags fetched with **one query per note inside a loop** (N+1 queries): fine with 10 notes, slow with 10,000 | quality | medium |
| S06 | Add "today's notes" view | compares the server's **local date** with timestamps stored in **UTC**: a user in India misses notes written between 00:00 and 05:30 | quality | high |
| S07 | Add note archiving | new public function, **no test** added | tests | medium |
| S08 | Fix flaky search test | test changed so it **asserts nothing** (always passes) | tests | high |
| S09 | Make JSON the default export format | **behaviour change** (default goes from txt to json) with README and changelog still saying txt, so users' existing scripts break silently | docs | medium |
| S10 | Add `--format json` to the CLI | new option **not in `--help` text or README** | docs | low |
| C01 | Refactor: split storage module | **clean**: pure move, tests unchanged and passing | — | — |
| C02 | Add tests for export edge cases | **clean**: tests only | — | — |
| C03 | Retry failed exports with backoff | **clean, but looks risky**: a loop with sleeps, capped at 3 attempts, with tests for each path. A reviewer that flags "possible infinite loop" here raises a false alarm | — | — |
| C04 | Switch internal report query to parameters | **clean, but looks security-sensitive**: replaces string-built SQL (with constant inputs only) by a parameterised query. It *fixes* a smell; flagging it as injection is a false alarm | — | — |

**Why the 4 clean PRs matter:** precision is your top metric (kickoff Q11). Any finding the reviewer raises on C01–C04 is a false alarm, and that's exactly what we most need to count.

## The 6 real click PRs (chosen in the next step, not now)

Selection rule, fixed **before** looking at any reviewer output:
1. a closed click issue labelled bug that names the PR which **introduced** the bug;
2. the PR's diff is under ~300 changed lines (fits the 5,000-token context budget, `S1-free-llm.md`);
3. the label = the bug the issue describes, at the lines the later fix changed.

## How a reviewer's answer is scored (pre-registered)

*(My proposal, derived from your precision-first answer, Q11. Change it if you disagree; once labels are committed, it's frozen.)*
- A reviewer finding **matches** a planted problem if it's in the **same file**, its lines **overlap the planted lines (±3 lines)**, and it comes from **any** specialist. Severity and wording don't need to match.
- **Precision** = matched findings ÷ all findings the reviewer raised (clean PRs included).
- **Recall** = planted problems matched ÷ planted problems (10 seeded + 6 real).
- Seeded and real are **reported separately**, never as one blended number.
- A finding that matches nothing is still **checked by you** before it's counted as a false alarm: it may be a real issue we didn't plant. That check is recorded, so the count can't drift afterwards.

## Your one step: a reviewer's eye on the 14

You've reviewed diffs for 11 years; this is where that judgement goes. For each row, the question is simply:
**would a careful senior reviewer flag this in a real PR?**

Write any row IDs that look wrong, too easy, or unrealistic, with one line why. Direction if all look fine: write "all fine".
- **Your answer (Nishant, 21 Oct 2026):**
  - S04 — unrealistic: not a real use case, just jargon
  - S05 — too easy: doesn't look real, no real use case
  - S06 — too easy: doesn't matter much
  - S09 — unrealistic: nobody raises a PR just to rename a parameter
  - C03, C04 — too easy: don't matter much
  - **Applied (v2 of the table above):** S04, S05, S06 and S09 replaced with production-style bugs: a partial write, N+1 queries, a UTC vs local-date bug, an undocumented breaking change. C03 and C04 replaced with clean PRs that **look** risky (a retry loop, a SQL change), so they actually test whether the reviewer raises false alarms.
  - **Claude's one disagreement, for the record:** a `bare except` swallowing a failed write (old S04) is a common real bug (silent data loss). It was dropped because the partial-write bug (new S04) tests the same "silent failure" idea more realistically.

- **If you check it:** the planted bugs are ones a real team cares about, and the evaluation can't be dismissed as toy examples.
- **If you skip it:** I build all 14 as listed. If some turn out unrealistic later, those PRs get rebuilt, and any scores already computed on them are thrown away.
- **If you don't decide:** the seeded PRs wait, and M1 stalls.

---

## Glossary

| Term | Meaning |
|---|---|
| **Seeded PR** | a PR we write with a problem planted on purpose, so the right answer is known |
| **SQL injection** | user text pasted into a database query, letting an attacker change the query |
| **Timing attack** | guessing a secret by measuring how long a comparison takes (`==` stops at the first wrong character) |
| **Path traversal** | a file name like `../../x` that escapes the intended folder |
| **Mutable default argument** | a Python bug: `def f(tags=[])` reuses the same list on every call |
| **Off-by-one** | a loop or range that's one item too long or too short |
| **Pre-registered** | the scoring rule and labels are committed to git *before* any scoring, so they can't be tuned to flatter a result |
| **Precision / recall** | of the findings raised, the share that were right / of the real problems, the share that were found |
| **Transaction** | a group of database writes that succeed or fail together, so nothing is left half-saved |
| **N+1 queries** | one query for a list, then one more query per item in it; slow as data grows |
| **UTC** | Coordinated Universal Time; India is UTC+05:30, so "today" starts 5½ hours apart |
| **Parameterised query** | a database query where user values are passed separately, never pasted into the SQL text; the standard fix for SQL injection |
| **Backoff** | waiting a little longer between each retry |
| **Breaking change** | a change that makes existing users' code or scripts stop working |
