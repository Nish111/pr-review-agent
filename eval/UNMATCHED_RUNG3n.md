# Unmatched findings, rung 3n: real or not? (Claude's verdicts; Nishant checks a sample)

These findings matched no known bug, so the hand check didn't cover them. Rung 4 needs every comment marked right or wrong.

**The rule Claude used (decision D2 = A in `eval/PREREG_RUNG4.md`):** `real` = the comment's claim is true **and** acting on it
fixes something wrong or risky that this PR introduced (documentation now wrong, new behaviour without a test, an actual bug or
hole). `not real` = the claim is false, or it's an omission that leaves nothing wrong (a new function not added to a list, a
changelog entry not written, an internal detail not documented), or the problem existed before the PR.

## U1 · PR S02 · `notes_svc/auth.py:7-7` · docs

- **Summary:** Docstring no longer mentions that token comparison is not constant-time, misleading about security behavior
- **Verdict:** not real — the docstring now matches the code (it no longer claims constant time); the actual fault is the == comparison, which other comments already report

## U2 · PR S03 · `notes_svc/export.py:10-10` · docs

- **Summary:** Docstring still states that the function adds a .txt extension, but the code now expects the full filename including extension
- **Verdict:** real — the docstring still says exports/<name>.txt, but the code now writes the name verbatim

## U3 · PR S04 · `notes_svc/notes.py:1-1` · docs

- **Summary:** Module docstring does not mention the newly added create_note_with_tags function
- **Verdict:** not real — an omission in a one-line module summary; nothing is wrong

## U4 · PR S07 · `notes_svc/notes.py:1-1` · docs

- **Summary:** Module docstring does not mention newly added archive_note functionality
- **Verdict:** not real — an omission in a one-line module summary

## U5 · PR S09 · `notes_svc/export.py:20-24` · security

- **Summary:** Unvalidated format string allows path traversal when constructing export file path
- **Verdict:** real — same as the quality comment: `fmt` reaches the file path unvalidated

## U6 · PR S10 · `notes_svc/cli.py:12-12` · docs

- **Summary:** CLI subcommand help text still mentions only .txt files despite added JSON format
- **Verdict:** real — the CLI help says exports/<file>.txt but --format json now writes .json: the planted docs problem, 4 lines from its label (same as rung 2)

## U7 · PR S10 · `notes_svc/export.py:13-13` · docs

- **Summary:** export_notes docstring still references only .txt output
- **Verdict:** real — the docstring still says .txt, but the function can now write .json (rung 2 found the same real, unplanted problem)

## U8 · PR S10 · `notes_svc/export.py:21-24` · tests

- **Summary:** JSON export format is added but no test verifies its behavior
- **Verdict:** real — true: the PR adds a JSON format and no test exercises it

## U9 · PR C03 · `notes_svc/export.py:10-11` · docs

- **Summary:** export_notes docstring does not mention retry/backoff behavior and possible OSError after max attempts
- **Verdict:** not real — an omission; the docstring isn't wrong

## U10 · PR C03 · `notes_svc/export.py:24-31` · quality

- **Summary:** Partial file may remain on disk after exhausting retries
- **Verdict:** not real — a failed write could leave a partial file before this PR too; the retry loop doesn't introduce it

## U11 · PR R1 · `src/click/termui.py:148-166` · docs

- **Summary:** Docstring does not mention that on non-Windows the full prompt string is now passed to the prompt function
- **Verdict:** not real — an omission about an internal detail; the docstring isn't wrong

## U12 · PR R5 · `src/click/testing.py:328-345` · docs

- **Summary:** CliRunner.invoke docstring does not mention that original file descriptors are preserved and may return -1
- **Verdict:** not real — an omission; the real problem with this PR is the fd itself (labelled R5), not its documentation
