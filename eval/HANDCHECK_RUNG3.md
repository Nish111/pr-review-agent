# Hand check: rung 3 matched findings (right reason?)

**What this is:** each finding below is in the right PLACE for a known bug. Your call: does it describe the SAME bug? Write `yes` or `no` (and a few words why, if you like) on each `Your answer` line.
**Do not open** `eval/results/rung3_judge.json` before finishing; the AI judge's verdicts are kept out of this file on purpose, so your answers stay independent.

**How to decide (the same rule as rung 2 and as the AI judge's instructions):** `yes` if the comment identifies the
**same underlying fault** as the known bug (same cause or same consequence); `no` if it raises a different concern near
the same lines. One case is new in rung 3, because the tests and docs reviewers often restate a bug in their own terms:
- the comment names the known bug **as the cause** ("SQL injection that no test covers", "docstring doesn't warn that
  keyword is put into the SQL") → it does identify the fault, so under the rule that is `yes`;
- the comment is only about a test or a document, and the known bug isn't what it describes ("new function has no test",
  when the known bug is something else) → `no`.
If you'd rather count the restated ones as `no`, write that choice here once, and apply it the same way in both files: ______

Expected time: about 45 minutes for both files (27 here, 28 in the other). Fill in **both** before running the judge's compare step.

## M1 · PR S01 · `notes_svc/notes.py:29`

- **Known bug:** keyword (user input) is pasted into the SQL text; a quote breaks out of the string
- **Reviewer said:** Docstring does not warn that `keyword` is interpolated directly into SQL, leading to potential injection or syntax errors
- **Reviewer's reasoning:** The function `search` now builds the SQL query with f-strings (lines 31‑33) inserting `user_id` and `keyword` directly, removing the previous parameterized query. The existing docstring (line 30) still only says "Notes whose title or body contains `keyword`." and does not mention the new requirement that `keyword` must be safe or escaped, nor the security implications.
- **Your answer:**  no

## M2 · PR S01 · `notes_svc/notes.py:31`

- **Known bug:** keyword (user input) is pasted into the SQL text; a quote breaks out of the string
- **Reviewer said:** User-supplied keyword is interpolated directly into SQL query
- **Reviewer's reasoning:** The search function builds the SQL statement using f-strings with the `keyword` parameter (lines 32-33). This allows an attacker to inject arbitrary SQL via a crafted keyword, bypassing intended filtering and potentially exposing or modifying data.
- **Your answer:** yes

## M3 · PR S01 · `notes_svc/notes.py:31`

- **Known bug:** keyword (user input) is pasted into the SQL text; a quote breaks out of the string
- **Reviewer said:** search() now interpolates user_id and keyword directly into SQL, introducing SQL injection risk that is not covered by any test
- **Reviewer's reasoning:** The diff replaces the safe parameterised query with an f‑string that embeds `user_id` and `keyword` (lines 31‑34). This changes behaviour: special characters in `keyword` (e.g., quotes, % or _) can alter the query semantics or cause syntax errors. No test in the suite exercises search() with such inputs, so the new vulnerability is untested.
- **Your answer:** yes

## M4 · PR S02 · `notes_svc/auth.py:3`

- **Known bug:** == on a secret leaks how many leading characters match; use hmac.compare_digest
- **Reviewer said:** Constant-time token comparison removed but no test verifies timing behavior
- **Reviewer's reasoning:** The diff deletes the import of `hmac` (line 3) and replaces `hmac.compare_digest` with a plain equality check (line 11). This changes the security property of `check_token` from constant‑time comparison to a potentially timing‑leaky comparison. No tests in the repository assert or measure constant‑time behavior, so the regression is untested.
- **Your answer:** yes

## M5 · PR S02 · `notes_svc/auth.py:6`

- **Known bug:** == on a secret leaks how many leading characters match; use hmac.compare_digest
- **Reviewer said:** Plain equality check leaks timing information for token comparison
- **Reviewer's reasoning:** The diff replaced the constant‑time `hmac.compare_digest` with a plain `==` comparison (line 11). This allows an attacker to perform a timing attack to guess valid tokens, violating secure authentication practices.
- **Your answer:** yes

## M6 · PR S03 · `notes_svc/export.py:14`

- **Known bug:** user-chosen name joined to EXPORT_DIR unchecked: '../../x' writes outside exports/
- **Reviewer said:** Export fails when `name` contains a subdirectory because the subdirectory is not created
- **Reviewer's reasoning:** Only `EXPORT_DIR` is created (line 14). If `name` includes a path separator (e.g., "subdir/file.txt"), `path = EXPORT_DIR / name` points to a non‑existent subdirectory, and `path.write_text` will raise `FileNotFoundError`.
- **Your answer:** no

## M7 · PR S03 · `notes_svc/export.py:15`

- **Known bug:** user-chosen name joined to EXPORT_DIR unchecked: '../../x' writes outside exports/
- **Reviewer said:** Empty `name` results in attempting to write to a directory, causing `IsADirectoryError`
- **Reviewer's reasoning:** If `name` is an empty string, `path = EXPORT_DIR / name` evaluates to `EXPORT_DIR` itself. The subsequent `path.write_text` call will try to write text to a directory, raising an exception.
- **Your answer:** yes

## M8 · PR S03 · `notes_svc/export.py:15`

- **Known bug:** user-chosen name joined to EXPORT_DIR unchecked: '../../x' writes outside exports/
- **Reviewer said:** User-controlled filename is written to the filesystem without validation, allowing path traversal
- **Reviewer's reasoning:** The function now builds the output path directly from the untrusted `name` argument (line 15: `path = EXPORT_DIR / name`). The previous validation that restricted `name` to a safe pattern and raised ValueError has been removed (lines removed: the regex definition and the `if not _SAFE_NAME.match(name): raise ValueError` block). This permits strings such as "../evil.txt" or absolute paths, causing the service to write files outside the intended `exports/` directory.
- **Your answer:** yes

## M9 · PR S04 · `notes_svc/notes.py:18`

- **Known bug:** note insert and tag insert are two separate transactions; a failed tag insert leaves the note saved without its tags
- **Reviewer said:** New function create_note_with_tags is not exercised by any test
- **Reviewer's reasoning:** The diff introduces create_note_with_tags (lines 18-25) which adds new behavior for creating a note together with its tags, but the test suite does not import or call this function, leaving the new functionality untested.
- **Your answer:** yes

## M10 · PR S04 · `notes_svc/notes.py:21`

- **Known bug:** note insert and tag insert are two separate transactions; a failed tag insert leaves the note saved without its tags
- **Reviewer said:** Note may be saved without its tags if tag insertion fails
- **Reviewer's reasoning:** The function creates the note in a separate transaction (create_note uses its own `with conn:` block at line 21) and then opens a new transaction for inserting tags (lines 22‑24). If the `executemany` fails (e.g., due to a constraint violation), the note remains persisted while its tags are not, resulting in inconsistent data.
- **Your answer:** yes

## M11 · PR S05 · `notes_svc/notes.py:29`

- **Known bug:** one tags query per note inside the loop; get_tags() already does it in one query
- **Reviewer said:** New function `list_notes_with_tags` is not covered by any test
- **Reviewer's reasoning:** The PR adds `list_notes_with_tags` (lines 29‑36) which returns notes with their tags, but the test suite only imports and exercises `list_notes`, `create_note`, `get_tags`, `search`, etc. No test references `list_notes_with_tags`, leaving the new behaviour untested.
- **Your answer:** no

## M12 · PR S05 · `notes_svc/notes.py:32`

- **Known bug:** one tags query per note inside the loop; get_tags() already does it in one query
- **Reviewer said:** Introduces N+1 query pattern causing many database round‑trips
- **Reviewer's reasoning:** list_notes_with_tags calls list_notes to fetch a page of notes, then iterates over each note and executes a separate SELECT query for its tags (lines 33‑35). For N notes this results in N+1 queries, which can degrade performance especially with larger pages.
- **Your answer:** yes

## M13 · PR S06 · `notes_svc/notes.py:30`

- **Known bug:** date.today() is the server's local date but created_at is UTC; for UTC+05:30 users, notes from 00:00-05:30 local are missed
- **Reviewer said:** New function `todays_notes` is not exercised by any test
- **Reviewer's reasoning:** The diff introduces `todays_notes` (lines 30‑37) which provides a new public API for retrieving notes created today, but the test suite contains no test that calls or validates this function.
- **Your answer:** yes

## M14 · PR S06 · `notes_svc/notes.py:30`

- **Known bug:** date.today() is the server's local date but created_at is UTC; for UTC+05:30 users, notes from 00:00-05:30 local are missed
- **Reviewer said:** Using local date for filtering UTC timestamps can miss notes created today in UTC
- **Reviewer's reasoning:** The function `todays_notes` computes `today` with `date.today().isoformat()` (local date) on line 32, then uses it in a LIKE pattern on the `created_at` column, which stores UTC ISO‑8601 timestamps via `utc_now()` (see notes_svc/db.py). If the server's local timezone differs from UTC, notes created on the current UTC day may be excluded, causing incorrect results.
- **Your answer:** yes

## M15 · PR S07 · `notes_svc/notes.py:18`

- **Known bug:** new public function, including an ownership check, with no test
- **Reviewer said:** New archive_note function is not exercised by any test
- **Reviewer's reasoning:** Lines 18‑25 introduce archive_note, a new behavior that should hide notes from list_notes, but the test suite contains no reference to archive_note, so this functionality is untested.
- **Your answer:** yes

## M16 · PR S07 · `notes_svc/notes.py:21`

- **Known bug:** new public function, including an ownership check, with no test
- **Reviewer said:** archive_note can insert duplicate 'archived' tags for the same note
- **Reviewer's reasoning:** The INSERT statement (lines 21-24) adds a row to the tags table without checking whether an 'archived' tag already exists for the note. Since the tags table has no uniqueness constraint, repeated calls will create duplicate rows, leading to duplicate tags in get_tags and potential logic errors elsewhere.
- **Your answer:** no

## M17 · PR S08 · `tests/test_notes.py:28`

- **Known bug:** the test no longer asserts anything, so it can never fail
- **Reviewer said:** Test no longer verifies search results, allowing regressions to go unnoticed
- **Reviewer's reasoning:** The original test asserted that searching for "milk" returns the expected titles (lines 25-27). The change replaces the assertion with a bare call to `search(conn, 1, "milk")` (line 28), removing verification of the function's output. This means failures in `search` will not be caught by the test suite, compromising correctness validation.
- **Your answer:** yes

## M18 · PR S08 · `tests/test_notes.py:28`

- **Known bug:** the test no longer asserts anything, so it can never fail
- **Reviewer said:** test_search_matches_title_or_body no longer asserts search results
- **Reviewer's reasoning:** The original test asserted that searching for "milk" returned the titles "groceries" and "work" (line with assert). The change replaces the assertion with a bare call to search, removing any verification of behavior, so the test can pass even if search is broken.
- **Your answer:** yes

## M19 · PR S09 · `notes_svc/export.py:12`

- **Known bug:** default output changes from .txt to .json but README and CHANGELOG still say txt; existing scripts that read exports/<name>.txt break
- **Reviewer said:** The docstring for export_notes does not document the new fmt parameter
- **Reviewer's reasoning:** The function signature now includes a fmt argument (line 12) with a default of "json", but the docstring (line 13) only mentions writing to exports/<name>.<fmt> without describing the purpose, accepted values, or default behavior of fmt, leaving the documentation incomplete for users.
- **Your answer:** yes

## M20 · PR S09 · `notes_svc/export.py:12`

- **Known bug:** default output changes from .txt to .json but README and CHANGELOG still say txt; existing scripts that read exports/<name>.txt break
- **Reviewer said:** Default JSON export format is not exercised by any test
- **Reviewer's reasoning:** The function export_notes now defaults to fmt="json" and includes JSON serialization logic (lines 12-22). However, the test suite only calls export_notes with fmt="txt" (see tests/test_export.py line 14) and does not verify the default JSON behavior, leaving the new functionality untested.
- **Your answer:** no

## M21 · PR S09 · `notes_svc/export.py:12`

- **Known bug:** default output changes from .txt to .json but README and CHANGELOG still say txt; existing scripts that read exports/<name>.txt break
- **Reviewer said:** Unvalidated `fmt` parameter can be used to traverse directories and write files outside the intended export directory
- **Reviewer's reasoning:** The function `export_notes` accepts a user-controlled `fmt` argument (line 12) and constructs the output path using `path = EXPORT_DIR / f"{name}.{fmt}"` (line 20) without validating `fmt`. If `fmt` contains path separators (e.g., "../evil"), the resulting path can escape the `EXPORT_DIR` and allow arbitrary file writes.
- **Your answer:** yes

## M22 · PR S09 · `notes_svc/export.py:12`

- **Known bug:** default output changes from .txt to .json but README and CHANGELOG still say txt; existing scripts that read exports/<name>.txt break
- **Reviewer said:** Default export format changed to JSON breaks CLI expectation of .txt files
- **Reviewer's reasoning:** The function now defaults to fmt="json" (line 12), but the CLI (notes_svc/cli.py line 17) still calls export_notes without specifying fmt, assuming the original .txt default. This results in the CLI creating a .json file instead of the documented .txt file, a regression in existing behavior.
- **Your answer:** yes

## M23 · PR S10 · `notes_svc/cli.py:16`

- **Known bug:** new --format option has no help text and the README usage isn't updated
- **Reviewer said:** New "--format" argument lacks a help description
- **Reviewer's reasoning:** The added argument at line 16 (`exp.add_argument("--format", default="txt", choices=["txt", "json"])`) does not provide a `help=` parameter, leaving users without guidance on its purpose.
- **Your answer:** yes

## M24 · PR R1 · `src/click/termui.py:62`

- **Known bug:** Prompts can contain colour codes. Before this PR click removed them when the terminal can't show colour; this PR passes the prompt straight to input(), so users on plain terminals see garbage like \x1b[31m.
- **Reviewer said:** The new err handling path in _readline_prompt (redirecting stdout to stderr) is not exercised by existing tests
- **Reviewer's reasoning:** Lines 62‑79 introduce a redirect of stdout to sys.stderr when err is True. No test in the repository calls _readline_prompt with err=True, nor verifies that the prompt is written to stderr. This new behavior is therefore untested.
- **Your answer:** yes

## M25 · PR R3 · `src/click/shell_completion.py:423`

- **Known bug:** To support multi-line help, the PR changed the format of the data click sends to the fish shell, and fish completion broke; the fix went back to the original format and escaped newlines and tabs instead.
- **Reviewer said:** Docstring for FishComplete.format_completion does not document the changed output format (now newline‑separated fields)
- **Reviewer's reasoning:** The method previously returned a comma‑separated string ("type,value\thelp") as shown by the removed lines. The new implementation (lines 433‑436) returns a newline‑separated string ("type\nvalue\nhelp"). The docstring added in lines 424‑432 only mentions escaping newlines but never states that the overall format has changed, leaving users unaware of the new delimiter and placeholder behavior.
- **Your answer:** no 

## M26 · PR R4 · `src/click/testing.py:119`

- **Known bug:** The EOFError was meant for prompts only, but it was put on the input stream's __next__, so any code that loops over the stream (for line in stream) now crashes at the end instead of stopping.
- **Reviewer said:** New EOFError on end of input in _NamedTextIOWrapper is not exercised by any test
- **Reviewer's reasoning:** The diff adds a __next__ implementation that converts StopIteration into EOFError (lines 119‑124). This changes the behavior of sys.stdin reads in CliRunner, but no test in the repository asserts that EOFError is raised when the input stream is exhausted, leaving the new behavior untested.
- **Your answer:** yes

## M27 · PR R5 · `src/click/testing.py:139`

- **Known bug:** fileno() on CliRunner's streams hands out the real terminal's file descriptor, so test code that redirects output at the OS level writes into the test runner's terminal and breaks pytest's own output capture.
- **Reviewer said:** New fileno() method on _NamedTextIOWrapper is not exercised by any test
- **Reviewer's reasoning:** The PR adds an original_fd parameter and overrides fileno() (lines 139‑152) to return the preserved descriptor. No existing test in the suite calls fileno() on a _NamedTextIOWrapper instance, so this new behaviour is untested.
- **Your answer:** yes

