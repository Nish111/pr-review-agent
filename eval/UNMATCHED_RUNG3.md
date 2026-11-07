# Unmatched findings, rung 3: real or not? (Claude's verdicts; Nishant checks a sample)

These findings matched no known bug, so the hand check didn't cover them. Rung 4 needs every comment marked right or wrong.

**The rule Claude used (decision D2 = A in `eval/PREREG_RUNG4.md`):** `real` = the comment's claim is true **and** acting on it
fixes something wrong or risky that this PR introduced (documentation now wrong, new behaviour without a test, an actual bug or
hole). `not real` = the claim is false, or it's an omission that leaves nothing wrong (a new function not added to a list, a
changelog entry not written, an internal detail not documented), or the problem existed before the PR.

## U1 · PR S02 · `notes_svc/auth.py:7-7` · docs

- **Summary:** Docstring no longer mentions that token comparison is not constant-time, omitting important security information
- **Verdict:** not real — the docstring now matches the code (it no longer claims constant time); the actual fault is the == comparison, which other comments already report

## U2 · PR S03 · `CHANGELOG.md:4-4` · docs

- **Summary:** Changelog entry still claims export creates `<name>.txt` files
- **Verdict:** not real — a changelog entry records what an old release did; it isn't wrong because later code changed

## U3 · PR S03 · `README.md:9-9` · docs

- **Summary:** README example still shows a fixed .txt extension
- **Verdict:** not real — Nishant's sample check (1 Nov 2026) disagreed with Claude's 'real'; his verdict replaces Claude's. (Claude's reason was: README says `--file mynotes` writes exports/mynotes.txt; after this PR it writes exports/mynotes (no extension), so the README is now wrong)

## U4 · PR S03 · `notes_svc/cli.py:14-14` · docs

- **Summary:** CLI help still restricts export name characters despite removal of validation
- **Verdict:** real — the help still promises the name is limited to letters, digits, _ and -, but the PR removed that check, so the help is now wrong

## U5 · PR S03 · `notes_svc/export.py:10-10` · docs

- **Summary:** Docstring mentions a .txt extension but function now writes the file exactly as given
- **Verdict:** real — the docstring still says exports/<name>.txt, but the code now writes the name verbatim

## U6 · PR S04 · `CHANGELOG.md:3-5` · docs

- **Summary:** CHANGELOG does not record the addition of `create_note_with_tags` helper
- **Verdict:** not real — an omission: nothing in the changelog is wrong

## U7 · PR S04 · `README.md:13-16` · docs

- **Summary:** README API section does not mention the new `create_note_with_tags` function
- **Verdict:** not real — an omission: the README API list isn't wrong, it just doesn't list the new helper

## U8 · PR S05 · `CHANGELOG.md:3-5` · docs

- **Summary:** CHANGELOG does not record the addition of tag display in note listings
- **Verdict:** not real — an omission: nothing in the changelog is wrong

## U9 · PR S05 · `README.md:13-15` · docs

- **Summary:** README API section does not document the new `list_notes_with_tags` function
- **Verdict:** not real — an omission: the README API list isn't wrong

## U10 · PR S06 · `CHANGELOG.md:3-5` · docs

- **Summary:** CHANGELOG does not record the addition of the "today's notes" view
- **Verdict:** not real — an omission

## U11 · PR S06 · `README.md:13-15` · docs

- **Summary:** README API section omits the new `todays_notes` function
- **Verdict:** not real — an omission

## U12 · PR S06 · `notes_svc/notes.py:1-1` · docs

- **Summary:** Module docstring does not list the newly added `todays_notes` function
- **Verdict:** not real — an omission in a one-line module summary

## U13 · PR S07 · `CHANGELOG.md:3-5` · docs

- **Summary:** CHANGELOG does not mention the new note archiving feature
- **Verdict:** not real — an omission

## U14 · PR S07 · `README.md:13-16` · docs

- **Summary:** README API list does not include the newly added archive_note function
- **Verdict:** not real — an omission

## U15 · PR S09 · `notes_svc/export.py:20-24` · quality

- **Summary:** Unvalidated fmt parameter can create arbitrary file paths
- **Verdict:** real — true: `name` is validated but the new `fmt` argument goes into the path unchecked, so a caller passing fmt='/../../x' writes outside exports/; a latent hole in a public function

## U16 · PR S10 · `CHANGELOG.md:4-4` · docs

- **Summary:** CHANGELOG does not record addition of JSON export format
- **Verdict:** not real — a changelog entry for an old release isn't wrong

## U17 · PR S10 · `README.md:7-10` · docs

- **Summary:** README still describes only txt export and does not mention JSON format
- **Verdict:** not real — the README still describes the default (txt) correctly; not mentioning --format is an omission

## U18 · PR S10 · `notes_svc/cli.py:12-12` · docs

- **Summary:** CLI help text still mentions only .txt export despite new JSON format support
- **Verdict:** real — the CLI help says exports/<file>.txt but --format json now writes .json: the planted docs problem, 4 lines from its label (same as rung 2)

## U19 · PR S10 · `notes_svc/export.py:12-24` · tests

- **Summary:** JSON export format added but not covered by any test
- **Verdict:** real — true: the PR adds a JSON format and no test exercises it

## U20 · PR S10 · `notes_svc/export.py:13-13` · docs

- **Summary:** export_notes docstring only mentions .txt output, ignoring new format option
- **Verdict:** real — the docstring still says .txt, but the function can now write .json (rung 2 found the same real, unplanted problem)

## U21 · PR S10 · `notes_svc/export.py:20-20` · security

- **Summary:** Unvalidated format parameter can lead to path traversal when constructing export file path
- **Verdict:** real — true for the function: `fmt` reaches the path unvalidated (the CLI limits it to txt/json, other callers aren't limited)

## U22 · PR C01 · `README.md:13-16` · docs

- **Summary:** README API list omits the newly re-exported get_tags function
- **Verdict:** not real — get_tags was already missing from the README before this PR; the PR only moved it

## U23 · PR C01 · `notes_svc/tags.py:1-15` · tests

- **Summary:** No test covers the new tags.get_tags public API
- **Verdict:** not real — behaviour is unchanged and already tested through the re-export in notes.py

## U24 · PR C03 · `README.md:9-10` · docs

- **Summary:** README does not document new retry/backoff behavior for exports
- **Verdict:** not real — retrying a failed write is an internal detail; nothing in the README is wrong

## U25 · PR C03 · `notes_svc/cli.py:12-12` · docs

- **Summary:** CLI help text does not mention that export may retry on failure
- **Verdict:** not real — nothing in the help text is wrong

## U26 · PR C03 · `notes_svc/export.py:15-15` · docs

- **Summary:** export_notes docstring does not mention retry behavior or possible OSError after max attempts
- **Verdict:** not real — an omission; the docstring isn't wrong

## U27 · PR C03 · `notes_svc/export.py:24-32` · quality

- **Summary:** Partial file may remain on persistent OSError after all retries
- **Verdict:** not real — a failed write could leave a partial file before this PR too; the retry loop doesn't introduce it

## U28 · PR R1 · `src/click/termui.py:172-173` · tests

- **Summary:** Existing tests that expect the prompt to be printed to stderr when err=True may now fail because the output is redirected via redirect_stdout
- **Verdict:** not real — speculative: redirect_stdout(sys.stderr) still sends the prompt to stderr when err=True, which is what such tests check
