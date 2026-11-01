# Hand check: rung 3n matched findings (right reason?)

**What this is:** each finding below is in the right PLACE for a known bug. Your call: does it describe the SAME bug? Write `yes` or `no` (and a few words why, if you like) on each `Your answer` line.
**Do not open** `eval/results/rung3n_judge.json` before finishing; the AI judge's verdicts are kept out of this file on purpose, so your answers stay independent.

**How to decide (the same rule as rung 2 and as the AI judge's instructions):** `yes` if the comment identifies the
**same underlying fault** as the known bug (same cause or same consequence); `no` if it raises a different concern near
the same lines. One case is new in rung 3, because the tests and docs reviewers often restate a bug in their own terms:
- the comment names the known bug **as the cause** ("SQL injection that no test covers", "docstring doesn't warn that
  keyword is put into the SQL") → it does identify the fault, so under the rule that is `yes`;
- the comment is only about a test or a document, and the known bug isn't what it describes ("new function has no test",
  when the known bug is something else) → `no`.
If you'd rather count the restated ones as `no`, write that choice here once, and apply it the same way in both files: ______

Expected time: about 45 minutes for both files (27 here, 28 in the other). Fill in **both** before running the judge's compare step.

## M1 · PR S01 · `notes_svc/notes.py:30`

- **Known bug:** keyword (user input) is pasted into the SQL text; a quote breaks out of the string
- **Reviewer said:** Docstring does not warn that `keyword` is interpolated directly into SQL and must be escaped
- **Reviewer's reasoning:** The function `search` now builds the SQL query with f‑string interpolation (lines 31‑34) inserting `keyword` directly into the query, which can cause syntax errors or SQL injection if the keyword contains quotes or special characters. The existing docstring (line 30) only states that notes containing `keyword` are returned and does not mention any required escaping or safety considerations.
- **Your answer:** no

## M2 · PR S01 · `notes_svc/notes.py:31`

- **Known bug:** keyword (user input) is pasted into the SQL text; a quote breaks out of the string
- **Reviewer said:** Search now builds SQL via string interpolation, introducing SQL injection risk that is not covered by tests
- **Reviewer's reasoning:** The function `search` directly interpolates `user_id` and `keyword` into the SQL statement (lines 31‑34), removing the previous parameterized query. This changes behaviour (introduces injection vulnerability) but there is no accompanying test to verify safe handling of malicious input.
- **Your answer:** yes

## M3 · PR S01 · `notes_svc/notes.py:31`

- **Known bug:** keyword (user input) is pasted into the SQL text; a quote breaks out of the string
- **Reviewer said:** User-controlled keyword is interpolated directly into SQL query
- **Reviewer's reasoning:** The search function builds the SQL statement using f-strings, inserting `user_id` and `keyword` directly (lines 32‑34). This allows an attacker to inject malicious SQL via the `keyword` parameter, bypassing intended filtering and potentially accessing or modifying data.
- **Your answer:** yes

## M4 · PR S02 · `notes_svc/auth.py:3`

- **Known bug:** == on a secret leaks how many leading characters match; use hmac.compare_digest
- **Reviewer said:** Removed constant-time token comparison, reintroducing timing attack vulnerability
- **Reviewer's reasoning:** The diff deletes the `import hmac` statement (line 3) and replaces `hmac.compare_digest(row["token"], token)` with a plain equality check `row["token"] == token` (line 11). This eliminates the constant‑time comparison that protected against timing attacks, changing the security behaviour of `check_token`.
- **Your answer:** yes

## M5 · PR S02 · `notes_svc/auth.py:11`

- **Known bug:** == on a secret leaks how many leading characters match; use hmac.compare_digest
- **Reviewer said:** Plain equality is used to compare authentication tokens, enabling timing attacks
- **Reviewer's reasoning:** The function `check_token` now returns `row["token"] == token` (line 11) instead of the constant‑time `hmac.compare_digest` that was previously used. Direct string comparison can leak timing information about the secret token, allowing an attacker to perform a brute‑force or timing attack.
- **Your answer:** yes

## M6 · PR S03 · `notes_svc/export.py:15`

- **Known bug:** user-chosen name joined to EXPORT_DIR unchecked: '../../x' writes outside exports/
- **Reviewer said:** User-controlled filename is used to construct a filesystem path without validation
- **Reviewer's reasoning:** The function now directly concatenates the untrusted `name` argument into a path (line 15: `path = EXPORT_DIR / name`) after removing the previous whitelist check. This allows path traversal (e.g., "../secret.txt") or absolute paths, enabling an attacker to write files outside the intended export directory.
- **Your answer:** yes

## M7 · PR S03 · `notes_svc/export.py:15`

- **Known bug:** user-chosen name joined to EXPORT_DIR unchecked: '../../x' writes outside exports/
- **Reviewer said:** User-supplied export name is not validated, allowing directory traversal and writes outside EXPORT_DIR
- **Reviewer's reasoning:** The function now directly concatenates the user-provided `name` to `EXPORT_DIR` (line 15) without any safety checks. Previously a regex `_SAFE_NAME` validated the name and prevented characters like "../". Removing that validation reintroduces the risk of paths such as "../secret.txt" escaping the intended export directory, leading to potential data loss or overwriting of arbitrary files.
- **Your answer:** yes

## M8 · PR S04 · `notes_svc/notes.py:21`

- **Known bug:** note insert and tag insert are two separate transactions; a failed tag insert leaves the note saved without its tags
- **Reviewer said:** create_note_with_tags inserts note and tags in separate transactions, risking orphan notes on tag insertion failure
- **Reviewer's reasoning:** The function first calls create_note (which commits its own transaction) on line 21, then opens a new transaction block on line 22 to insert tags. If the INSERT into tags fails, the note has already been committed, leaving an orphan note without tags. This behavior is not atomic and is not covered by existing tests.
- **Your answer:** no

## M9 · PR S04 · `notes_svc/notes.py:21`

- **Known bug:** note insert and tag insert are two separate transactions; a failed tag insert leaves the note saved without its tags
- **Reviewer said:** Note and its tags are saved in separate transactions, causing possible orphan notes if tag insertion fails
- **Reviewer's reasoning:** The function `create_note_with_tags` first calls `create_note`, which commits its INSERT inside its own `with conn:` block (lines 21-22). It then opens a second `with conn:` block to insert tags (lines 22-24). If the tag insertion raises an exception, the note remains persisted while its tags are not, leading to inconsistent data.
- **Your answer:** yes

## M10 · PR S05 · `notes_svc/notes.py:1`

- **Known bug:** one tags query per note inside the loop; get_tags() already does it in one query
- **Reviewer said:** Module docstring does not mention the newly added list_notes_with_tags function
- **Reviewer's reasoning:** The top‑level module docstring (line 1) lists the available operations as "create, list, search, tag" but the PR adds a new public function `list_notes_with_tags` (lines 29‑36). The docstring is now incomplete and does not inform users of this new capability.
- **Your answer:** yes

## M11 · PR S05 · `notes_svc/notes.py:32`

- **Known bug:** one tags query per note inside the loop; get_tags() already does it in one query
- **Reviewer said:** N+1 query pattern causes a separate DB query per note
- **Reviewer's reasoning:** The function `list_notes_with_tags` iterates over each note returned by `list_notes` and executes a separate `SELECT tag FROM tags WHERE note_id = ?` query for each note (lines 33-35). This results in one query per note, leading to potential performance degradation when many notes are listed.
- **Your answer:** yes

## M12 · PR S06 · `notes_svc/notes.py:32`

- **Known bug:** date.today() is the server's local date but created_at is UTC; for UTC+05:30 users, notes from 00:00-05:30 local are missed
- **Reviewer said:** Using local date to filter UTC timestamps may miss notes created today in UTC
- **Reviewer's reasoning:** The function `todays_notes` computes `today` with `date.today().isoformat()` (local date) on line 32, then filters `created_at` (stored in UTC by `utc_now()`) using a LIKE pattern on line 35. If the server's local timezone differs from UTC, notes created after midnight UTC but before local midnight will be excluded, leading to incorrect results.
- **Your answer:** yes

## M13 · PR S07 · `notes_svc/notes.py:18`

- **Known bug:** new public function, including an ownership check, with no test
- **Reviewer said:** Function trusts caller-provided user_id, enabling IDOR to archive others' notes
- **Reviewer's reasoning:** The `archive_note` function receives `user_id` as a parameter and uses it directly in the SQL query (lines 22-24). If the caller supplies an arbitrary user_id, they can archive notes belonging to other users, leading to an insecure direct object reference.
- **Your answer:** yes

## M14 · PR S07 · `notes_svc/notes.py:18`

- **Known bug:** new public function, including an ownership check, with no test
- **Reviewer said:** New archive_note function is not covered by any test
- **Reviewer's reasoning:** The PR introduces the archive_note function (lines 18‑25) which adds an 'archived' tag to a note. No existing test suite is shown to exercise this new behavior, leaving the functionality unverified.
- **Your answer:** no

## M15 · PR S07 · `notes_svc/notes.py:20`

- **Known bug:** new public function, including an ownership check, with no test
- **Reviewer said:** Duplicate archiving can raise an IntegrityError instead of returning False
- **Reviewer's reasoning:** The function inserts a row into the tags table without checking whether an 'archived' tag already exists for the note. If the tags table enforces a UNIQUE constraint on (note_id, tag), a second call to archive_note for the same note will cause sqlite3.IntegrityError, breaking the service instead of returning False.
- **Your answer:** yes

## M16 · PR S08 · `tests/test_notes.py:24`

- **Known bug:** the test no longer asserts anything, so it can never fail
- **Reviewer said:** search test no longer asserts expected results
- **Reviewer's reasoning:** The original assertion checking that search returns the expected titles was removed (line 28 changed from an assert to a bare function call). This weakens the test, allowing regressions in search behavior to go undetected.
- **Your answer:** yes

## M17 · PR S08 · `tests/test_notes.py:25`

- **Known bug:** the test no longer asserts anything, so it can never fail
- **Reviewer said:** Test no longer verifies search results, allowing regressions to go unnoticed
- **Reviewer's reasoning:** The original assertion `assert {n["title"] for n in search(conn, 1, "milk")} == {"groceries", "work"}` was removed and replaced with a bare call `search(conn, 1, "milk")`. This eliminates verification of the search function's correctness, so failures in search logic will not be caught by this test.
- **Your answer:** yes

## M18 · PR S09 · `notes_svc/export.py:12`

- **Known bug:** default output changes from .txt to .json but README and CHANGELOG still say txt; existing scripts that read exports/<name>.txt break
- **Reviewer said:** The new `fmt` parameter is not documented in the function docstring
- **Reviewer's reasoning:** The function signature now includes a `fmt: str = "json"` argument, but the docstring only mentions the output path format and does not describe the purpose, allowed values, or default behavior of the `fmt` parameter. This omission can lead to user confusion about how to request different export formats.
- **Your answer:** yes

## M19 · PR S09 · `notes_svc/export.py:12`

- **Known bug:** default output changes from .txt to .json but README and CHANGELOG still say txt; existing scripts that read exports/<name>.txt break
- **Reviewer said:** Default JSON export format is not exercised by any test
- **Reviewer's reasoning:** The function signature now defaults to fmt="json" (line 12) and adds JSON serialization logic (lines 21‑22). No test in the repository calls export_notes without specifying fmt, so the new default behavior is untested.
- **Your answer:** yes

## M20 · PR R1 · `src/click/termui.py:69`

- **Known bug:** Prompts can contain colour codes. Before this PR click removed them when the terminal can't show colour; this PR passes the prompt straight to input(), so users on plain terminals see garbage like \x1b[31m.
- **Reviewer said:** IndexError when prompt text is empty on Windows
- **Reviewer's reasoning:** The function `_readline_prompt` slices the prompt string assuming it has at least one character: it calls `text[:-1]` and `text[-1:]`. If `text` is an empty string (possible if a caller passes an empty prompt), `text[-1:]` raises an IndexError, causing the prompt to crash on Windows platforms.
- **Your answer:** yes

## M21 · PR R1 · `src/click/termui.py:76`

- **Known bug:** Prompts can contain colour codes. Before this PR click removed them when the terminal can't show colour; this PR passes the prompt straight to input(), so users on plain terminals see garbage like \x1b[31m.
- **Reviewer said:** Prompt output is redirected to stderr when err=True, causing existing tests that capture stdout to miss the prompt
- **Reviewer's reasoning:** The new _readline_prompt function adds a redirect_stdout to sys.stderr when err is true (lines 76‑79). Previously, only the first part of the prompt was sent to stderr via echo, and the rest was printed by the input function to stdout. Tests that capture stdout to assert prompt appearance will no longer see the prompt, weakening their assertions.
- **Your answer:** yes

## M22 · PR R3 · `src/click/shell_completion.py:182`

- **Known bug:** To support multi-line help, the PR changed the format of the data click sends to the fish shell, and fish completion broke; the fix went back to the original format and escaped newlines and tabs instead.
- **Reviewer said:** Fish completion script incorrectly iterates over formatted completions because each completion now contains internal newlines
- **Reviewer's reasoning:** The `format_completion` method now returns a string with newline characters separating type, value, and help (lines 433-436). The fish script builds `$response` as a list of these strings separated by newlines and then iterates with `for completion in $response;` (line 182). In fish, the `for` loop splits its input on whitespace, which includes newlines, so each internal newline inside a single completion causes the loop to treat the type, value, and help as separate `$completion` items. Consequently, the subsequent `string split \n $completion` (line 183) receives only a fragment (e.g., the type) and fails to produce the expected three‑element `metadata` array, breaking completion handling.
- **Your answer:** no

## M23 · PR R3 · `src/click/shell_completion.py:182`

- **Known bug:** To support multi-line help, the PR changed the format of the data click sends to the fish shell, and fish completion broke; the fix went back to the original format and escaped newlines and tabs instead.
- **Reviewer said:** Fish completion output format changed from comma‑separated to newline‑separated, breaking tests that assert the old format
- **Reviewer's reasoning:** The shell script now splits completion metadata on newlines (line 183) and emits either "value\thelp" or just "value" (lines 190‑194). Previously it split on commas (line 182) and always emitted a tab‑separated help field only when present. Tests that verify the fish completion script parses comma‑separated metadata or that the help field is omitted when not provided will no longer exercise the intended behavior and will likely fail.
- **Your answer:** yes

## M24 · PR R3 · `src/click/shell_completion.py:423`

- **Known bug:** To support multi-line help, the PR changed the format of the data click sends to the fish shell, and fish completion broke; the fix went back to the original format and escaped newlines and tabs instead.
- **Reviewer said:** Python format_completion method now always includes a help field (default "_"), breaking tests that expect its omission when help is None
- **Reviewer's reasoning:** The method previously returned "type,value\thelp" only when item.help was truthy, otherwise "type,value" (lines 423‑425 in the diff). The new implementation always returns three newline‑separated parts, inserting "_" when help is missing (lines 433‑436). Tests that assert the output lacks a help component for items without help will now pass incorrectly or fail, reducing test coverage of the conditional behavior.
- **Your answer:** yes

## M25 · PR R4 · `src/click/testing.py:119`

- **Known bug:** The EOFError was meant for prompts only, but it was put on the input stream's __next__, so any code that loops over the stream (for line in stream) now crashes at the end instead of stopping.
- **Reviewer said:** Iterating over sys.stdout or sys.stderr now raises EOFError instead of StopIteration
- **Reviewer's reasoning:** The added __next__ method (lines 119‑124) catches StopIteration from the base TextIOWrapper and re‑raises EOFError. This changes the iterator protocol for all _NamedTextIOWrapper instances, including the ones used for sys.stdout and sys.stderr (created at lines 336‑345). Code that iterates over these streams expecting StopIteration will now receive an unexpected EOFError, potentially breaking existing behaviour.
- **Your answer:** yes

## M26 · PR R4 · `src/click/testing.py:119`

- **Known bug:** The EOFError was meant for prompts only, but it was put on the input stream's __next__, so any code that loops over the stream (for line in stream) now crashes at the end instead of stopping.
- **Reviewer said:** New EOFError on end of input is not exercised by any test
- **Reviewer's reasoning:** The added __next__ method now raises EOFError when the underlying stream is exhausted (lines 119‑124). This changes the observable behavior of input handling, but the test suite does not contain any test that verifies that EOFError is raised on end‑of‑input, nor that the CLI runner now propagates this exception. Consequently the new behavior is untested.
- **Your answer:** yes

## M27 · PR R5 · `src/click/testing.py:103`

- **Known bug:** fileno() on CliRunner's streams hands out the real terminal's file descriptor, so test code that redirects output at the OS level writes into the test runner's terminal and breaks pytest's own output capture.
- **Reviewer said:** The new original_fd preservation feature is not exercised by any test
- **Reviewer's reasoning:** Lines 103‑152 introduce an optional original_fd parameter and a fileno() override to expose the original file descriptor of redirected streams. No test code in the repository references this parameter or verifies that the original descriptor is correctly returned, leaving the new behavior untested.
- **Your answer:** no

## M28 · PR R5 · `src/click/testing.py:139`

- **Known bug:** fileno() on CliRunner's streams hands out the real terminal's file descriptor, so test code that redirects output at the OS level writes into the test runner's terminal and breaks pytest's own output capture.
- **Reviewer said:** Existing tests expecting sys.stdout.fileno() to raise now receive -1
- **Reviewer's reasoning:** The new fileno() implementation returns -1 when no original_fd is provided (lines 150‑152). The CliRunner now constructs _NamedTextIOWrapper with original_fd set to the result of _safe_fileno, which returns -1 for streams without a fileno (lines 363‑370, 386‑392, 394‑401). Previously, calling fileno() on the wrapper would raise an OSError because the underlying BytesIO has no fileno. Tests that assert an exception from sys.stdout.fileno() will now fail or become ineffective.
- **Your answer:** yes

