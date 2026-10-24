# M1 · The 5 real click PRs: what they are, and one decision

Rewritten 24 Oct 2026 (v2), because v1 didn't make the purpose or the task clear.

## The intention, in three sentences

Later, our reviewer bot will be shown each of these 5 click PRs **exactly as it looked before it was merged**, and
asked to review it. We already know, from click's own history, that each PR shipped a bug that click's
maintainers later had to fix. So the test is simply: **does our bot spot that bug, which click's human reviewers missed?**

You don't need to review the PRs. The only open question is how to *count* the results fairly (the decision at the end).
The cards below are just so you know what's in the set.

---

## The 5 PRs, each on one card

Each card shows the code **as the PR added it**, what went wrong, and where click says so.

### R1: click [#2969](https://github.com/pallets/click/pull/2969), "Fix readline backspace/line-wrapping on linux"
```python
    if err:
        with redirect_stdout(sys.stderr):
            return func(text)
    return func(text)            # <- the prompt text goes to input() as-is
```
- **The bug:** prompts can contain colour codes. Before this PR, click removed them when the terminal can't show colour. This PR started passing the prompt straight to `input()`, so users on plain terminals saw garbage like `\x1b[31m`.
- **Source:** click `CHANGES.md`, 8.5.0: "lost in 8.4.0 when #2969 began writing the prompt with input() directly". Fixed by [#3653](https://github.com/pallets/click/pull/3653).

### R2: click [#1572](https://github.com/pallets/click/pull/1572), "Add file-like pager: click.get_pager_file()" (two bugs)
```python
    f = tempfile.NamedTemporaryFile(mode="wb", delete=False)   # <- bug 1: binary mode
    try:
        yield t.cast(t.BinaryIO, f), encoding, color
        f.flush()
        f.close()
        subprocess.call([str(cmd_path), f.name])
    finally:
        os.unlink(f.name)                                      # <- bug 2: file may still be open
```
- **Bug 1:** the file is opened for bytes, but callers write text, so on Windows writing to the pager crashed with `TypeError`.
- **Bug 2:** if an error happens before `f.close()`, the file is deleted while still open. Windows refuses, and that second error hides the real one.
- **Source:** `CHANGES.md` 8.5.0: "Regression introduced in 8.4.0 by #1572". Fixed by [#3739](https://github.com/pallets/click/pull/3739) and [#3764](https://github.com/pallets/click/pull/3764).

### R3: click [#3126](https://github.com/pallets/click/pull/3126), "Ensure fish completion handles multiline help strings"
```python
        value = item.value.replace("\n", r"\n")
        help_escaped = help_.replace("\n", r"\n")
        return f"{item.type}\n{value}\n{help_escaped}"
```
- **The bug:** to support multi-line help text, the PR changed the format of the data click sends to the fish shell (one value per line), and fish completion broke. The fix went back to the original format and escaped newlines and tabs instead (wording from click's changelog; the exact failure is in issue [#3502](https://github.com/pallets/click/issues/3502), which I haven't been able to open).
- **Source:** `CHANGES.md` 8.4.2: "Fix Fish shell completion broken in 8.4.0 by #3126". Fixed by [#3504](https://github.com/pallets/click/pull/3504).

### R4: click [#2934](https://github.com/pallets/click/pull/2934), "Raise an exception on end of input in CliRunner"
```python
    def __next__(self) -> str:
        try:
            line = super().__next__()
        except StopIteration as e:
            raise EOFError() from e      # <- changes how EVERY reader of this stream ends
        return line
```
- **The bug:** the change was meant for prompts only, but it was put on the stream itself, so any code that simply looped over the input (`for line in stream`) now crashed at the end instead of stopping.
- **Source:** the fix's own commit title: "Fix regression related to EOF introduced in 262bdf0 (#2940)".

### R5: click commit `8762c77`, "Expose original file descriptor in CliRunner"
```python
        def _safe_fileno(stream):
            try:
                return stream.fileno()           # <- hands out the REAL terminal's file number
            except (AttributeError, io.UnsupportedOperation):
                return -1
```
- **The bug:** test code that redirected output at the operating-system level now wrote into the real terminal of the test runner, which broke pytest's own output capture.
- **Source:** `CHANGES.md` 8.4.0, which reverts the 8.3.3 change because it "broke Pytest's fd-level capture teardown". Fixed by [#3391](https://github.com/pallets/click/pull/3391).

**Count:** 5 PRs, 6 bugs (R2 has two). It's 5 rather than ~6 because click names the guilty PR for only 5 bugs. Adding a guessed one would bring back our own bias.

---

## The one decision: how to count these 5

Some of these bugs are visible in the diff (R2 bug 1, R4). Others only show up on Windows, or inside pytest
(R2 bug 2, R5), and no reviewer could reasonably see them from the diff alone. Counting all 6 as one
"recall" number would punish the bot for missing the invisible ones.

**Option A (recommended): no number, report each PR on its own.** With only 5 PRs a percentage means little anyway.
The write-up shows a table: PR, bug, found / missed, and what the bot said. Readers judge each case.
- **If you choose A:** no work for you now; the result is honest, and you only look at the 5 bot answers when they exist (M2 onwards).
- **If you choose B instead:** you read each card above and mark it `fair` (a reviewer could see it in the diff) or `hard` (couldn't). Recall is then reported for "fair" bugs only. About 15 minutes of your judgement now.
- **If you don't decide:** we default to A.

**Your answer** (A or B; if B, mark R1–R5 fair/hard): A 
- 

## Glossary

| Term | Meaning |
|---|---|
| **Introducing PR** | the PR that first put the bug in; this is what the bot reviews |
| **Recall** | of the real bugs, the share the bot found |
| **Colour codes (ANSI)** | hidden characters that make terminal text coloured; plain terminals print them as garbage |
| **Pager** | the program (like `less`) that shows long output one screen at a time |
| **File descriptor** | the number the operating system uses to identify an open file or terminal |
| **EOF / StopIteration** | "end of input" signals; one stops a loop quietly, the other is an error |
