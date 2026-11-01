# Sample check of Claude's unmatched-finding verdicts (decision D2 = A)

10 verdicts drawn at random (fixed seed 20261101, so anyone can redraw the same 10) from `eval/UNMATCHED_RUNG3.md` and `eval/UNMATCHED_RUNG3n.md`.
For each: read the comment, Claude's verdict and its reason below, then write `agree` or `disagree` (and why, if you disagree).
**3 or more `disagree` → you check all of them** (that's the rule you chose). Fewer → Claude's verdicts stand, and your disagreements replace Claude's on those items.

**The rule Claude used:** `real` = the comment's claim is true **and** acting on it fixes something wrong or risky that this PR
introduced (documentation now wrong, new behaviour without a test, an actual bug or hole). `not real` = the claim is false, or
it's an omission that leaves nothing wrong (a new function not added to a list, no changelog entry, an internal detail not
documented), or the problem existed before the PR. Disagree with the rule itself? Say so here: ______

## U3 in `eval/UNMATCHED_RUNG3.md` · PR S03 · `README.md:9-9` · docs reviewer

- **Comment:** README example still shows a fixed .txt extension
- **Claude's verdict:** real
- **Claude's reason:** README says `--file mynotes` writes exports/mynotes.txt; after this PR it writes exports/mynotes (no extension), so the README is now wrong
- **Your answer:** disagree

## U4 in `eval/UNMATCHED_RUNG3.md` · PR S03 · `notes_svc/cli.py:14-14` · docs reviewer

- **Comment:** CLI help still restricts export name characters despite removal of validation
- **Claude's verdict:** real
- **Claude's reason:** the help still promises the name is limited to letters, digits, _ and -, but the PR removed that check, so the help is now wrong
- **Your answer:** agree

## U5 in `eval/UNMATCHED_RUNG3.md` · PR S03 · `notes_svc/export.py:10-10` · docs reviewer

- **Comment:** Docstring mentions a .txt extension but function now writes the file exactly as given
- **Claude's verdict:** real
- **Claude's reason:** the docstring still says exports/<name>.txt, but the code now writes the name verbatim
- **Your answer:** agree

## U6 in `eval/UNMATCHED_RUNG3.md` · PR S04 · `CHANGELOG.md:3-5` · docs reviewer

- **Comment:** CHANGELOG does not record the addition of `create_note_with_tags` helper
- **Claude's verdict:** not real
- **Claude's reason:** an omission: nothing in the changelog is wrong
- **Your answer:** agree

## U8 in `eval/UNMATCHED_RUNG3.md` · PR S05 · `CHANGELOG.md:3-5` · docs reviewer

- **Comment:** CHANGELOG does not record the addition of tag display in note listings
- **Claude's verdict:** not real
- **Claude's reason:** an omission: nothing in the changelog is wrong
- **Your answer:** agree

## U15 in `eval/UNMATCHED_RUNG3.md` · PR S09 · `notes_svc/export.py:20-24` · quality reviewer

- **Comment:** Unvalidated fmt parameter can create arbitrary file paths
- **Claude's verdict:** real
- **Claude's reason:** true: `name` is validated but the new `fmt` argument goes into the path unchecked, so a caller passing fmt='/../../x' writes outside exports/; a latent hole in a public function
- **Your answer:** agree

## U18 in `eval/UNMATCHED_RUNG3.md` · PR S10 · `notes_svc/cli.py:12-12` · docs reviewer

- **Comment:** CLI help text still mentions only .txt export despite new JSON format support
- **Claude's verdict:** real
- **Claude's reason:** the CLI help says exports/<file>.txt but --format json now writes .json: the planted docs problem, 4 lines from its label (same as rung 2)
- **Your answer:** agree

## U22 in `eval/UNMATCHED_RUNG3.md` · PR C01 · `README.md:13-16` · docs reviewer

- **Comment:** README API list omits the newly re-exported get_tags function
- **Claude's verdict:** not real
- **Claude's reason:** get_tags was already missing from the README before this PR; the PR only moved it
- **Your answer:** agree

## U26 in `eval/UNMATCHED_RUNG3.md` · PR C03 · `notes_svc/export.py:15-15` · docs reviewer

- **Comment:** export_notes docstring does not mention retry behavior or possible OSError after max attempts
- **Claude's verdict:** not real
- **Claude's reason:** an omission; the docstring isn't wrong
- **Your answer:** agree

## U9 in `eval/UNMATCHED_RUNG3n.md` · PR C03 · `notes_svc/export.py:10-11` · docs reviewer

- **Comment:** export_notes docstring does not mention retry/backoff behavior and possible OSError after max attempts
- **Claude's verdict:** not real
- **Claude's reason:** an omission; the docstring isn't wrong
- **Your answer:** agree
