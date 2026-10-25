# Hand check: rung 2 matched findings (right reason?)

**What this is:** each finding below is in the right PLACE for a known bug. Your call: does it describe the SAME bug? Write `yes` or `no` (and a few words why, if you like) on each `Your answer` line.
**Do not open** `eval/results/rung2_judge.json` before finishing; the AI judge's verdicts are kept out of this file on purpose, so your answers stay independent.

## M1 · PR S01 · `notes_svc/notes.py:31`

- **Known bug:** keyword (user input) is pasted into the SQL text; a quote breaks out of the string
- **Reviewer said:** SQL injection vulnerability due to interpolating user input directly into query
- **Reviewer's reasoning:** The new code builds the SQL statement by embedding `user_id` and `keyword` directly into the string (lines 32‑34). If either value contains malicious content (e.g., a quote or SQL fragment), it can alter the query semantics or execute arbitrary SQL, leading to a security breach.
- **Your answer:**  yes

## M2 · PR S02 · `notes_svc/auth.py:11`

- **Known bug:** == on a secret leaks how many leading characters match; use hmac.compare_digest
- **Reviewer said:** Plain token comparison introduces timing attack vulnerability
- **Reviewer's reasoning:** The function now returns `row["token"] == token` (line 11), which performs a short-circuit string equality check that can leak timing information about the token. The previous implementation used `hmac.compare_digest` for constant‑time comparison, which mitigates this risk. Removing it reintroduces a security hole in authentication.
- **Your answer:** yes

## M3 · PR S03 · `notes_svc/export.py:15`

- **Known bug:** user-chosen name joined to EXPORT_DIR unchecked: '../../x' writes outside exports/
- **Reviewer said:** Missing validation allows path traversal and arbitrary file writes
- **Reviewer's reasoning:** The function now builds the export path directly from the user‑provided `name` without any safety checks (see line 15: `path = EXPORT_DIR / name`). This permits names like "../secret.txt" or absolute paths, causing files to be written outside the intended `exports` directory, leading to potential data loss or security breaches.
- **Your answer:** yes

## M4 · PR S04 · `notes_svc/notes.py:21`

- **Known bug:** note insert and tag insert are two separate transactions; a failed tag insert leaves the note saved without its tags
- **Reviewer said:** Note creation and tag insertion are not performed atomically, risking orphan notes if tag insertion fails
- **Reviewer's reasoning:** The function `create_note_with_tags` first calls `create_note`, which commits the note insertion in its own transaction (lines 21-22). It then opens a separate transaction to insert tags (lines 22-24). If the tag insertion fails, the note remains in the database without its tags, leading to inconsistent state.
- **Your answer:** yes

## M5 · PR S06 · `notes_svc/notes.py:30`

- **Known bug:** date.today() is the server's local date but created_at is UTC; for UTC+05:30 users, notes from 00:00-05:30 local are missed
- **Reviewer said:** Using local date to filter UTC timestamps can miss or include notes from the wrong day
- **Reviewer's reasoning:** The function `todays_notes` computes `today = date.today().isoformat()` which yields the server's local date, but notes are stored with `created_at` set by `utc_now()` (UTC time). Comparing the local date string with a UTC timestamp via `LIKE` may exclude notes created after midnight UTC or include notes from a different local day, leading to incorrect results.
- **Your answer:** yes

## M6 · PR S07 · `notes_svc/notes.py:18`

- **Known bug:** new public function, including an ownership check, with no test
- **Reviewer said:** Inserting an 'archived' tag without checking for existing tag can cause duplicate entries or integrity errors
- **Reviewer's reasoning:** The function `archive_note` unconditionally executes an INSERT SELECT to add the tag 'archived' (lines 21‑24). If the note is already archived, this will attempt to insert a duplicate (note_id, 'archived') row, which will violate a typical UNIQUE constraint on (note_id, tag) and raise an exception, breaking the operation.
- **Your answer:** yes

## M7 · PR S08 · `tests/test_notes.py:28`

- **Known bug:** the test no longer asserts anything, so it can never fail
- **Reviewer said:** Test no longer verifies search results
- **Reviewer's reasoning:** The original test asserted that the titles returned by `search(conn, 1, "milk")` matched the expected set {"groceries", "work"}. The change replaces the assert with a bare function call, removing any verification of the search output, so the test will pass even if `search` returns incorrect results.
- **Your answer:** no

## M8 · PR R3 · `src/click/shell_completion.py:182`

- **Known bug:** CHANGES.md 8.4.2: 'Fix Fish shell completion broken in 8.4.0 by #3126'
- **Reviewer said:** Fish completion script splits on literal "\n" instead of actual newline, causing parsing errors
- **Reviewer's reasoning:** The updated script uses `set -l metadata (string split \n $completion);` (lines 182‑184). In fish, the `string split` command does not interpret escape sequences, so the delimiter `\n` is taken as the two characters backslash and "n" rather than a newline. This prevents the completion string (which is newline‑delimited) from being split into its type, value, and help components, breaking fish completion handling.
- **Your answer:** yes

## M9 · PR R4 · `src/click/testing.py:119`

- **Known bug:** Fix commit title: 'testing/CliRunner: Fix regression related to EOF introduced in 262bdf0 (#2940)'
- **Reviewer said:** __next__ raises EOFError instead of StopIteration, breaking iterator semantics
- **Reviewer's reasoning:** The overridden __next__ method catches StopIteration from the superclass and re‑raises EOFError (lines 119‑124). This means any code that iterates over the _NamedTextIOWrapper (e.g., "for line in sys.stdin:") will receive EOFError instead of the expected StopIteration, violating the iterator protocol and potentially causing uncaught exceptions.
- **Your answer:** no


---

## Round 2 · the 3 disagreements (written 25 Oct 2026, after your answers above were final)

Your first answers above are **kept unchanged** and get reported as they are. You and the AI judge agreed on 6 of 9.
On these 3 you disagreed. Below is each one, with the judge's verdict and my reading, so you can look again.
**Your round-2 answer counts as the official one**, and the write-up shows both rounds, so nothing is hidden.

### M6 · S07 · you: **yes** · judge: **no**
- **Known bug:** the PR adds a new public function (`archive_note`) with **no test**.
- **Reviewer said:** archiving twice inserts a **duplicate tag** row.
- **My reading:** a different problem. It's about duplicate data, not about the missing test. The reviewer never mentions tests.
- **Round-2 answer (Nishant, 25 Oct):** no

### M7 · S08 · you: **no** · judge: **yes**
- **Known bug:** the test was changed so it **asserts nothing** and can never fail.
- **Reviewer said:** "Test no longer verifies search results… the assert was replaced with a bare function call… the test will pass even if `search` returns incorrect results."
- **My reading:** the same bug, in different words.
- **Round-2 answer (Nishant, 25 Oct):** no

### M9 · R4 · you: **no** · judge: **yes**
- **Known bug (as labelled):** only the fix commit's title, "Fix regression related to EOF". The plain-words version is in `REAL_PRS_REVIEW.md`, card R4: *"the change was put on the stream itself, so any code that simply looped over the input (`for line in stream`) now crashed at the end instead of stopping."*
- **Reviewer said:** `__next__` raises `EOFError` instead of `StopIteration`, so code that iterates the stream gets an exception.
- **My reading:** the same bug. **My fault:** this label only carried the commit title, which is too vague to judge against. For rungs 3 and 4, every real label will carry the plain-words description (to be fixed in the next pre-registration, before any scoring).
- **Round-2 answer (Nishant, 25 Oct):** yes
