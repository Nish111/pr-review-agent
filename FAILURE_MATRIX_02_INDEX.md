# Failure matrix 02 · Ingestion & index

Draft v1, 25 Oct 2026. It follows the same loop as matrix 01: purpose and contract → assumptions → failure modes →
prevention and detection → recovery → tests and evidence. The brief's §3 row for this group says:
*chunking, freshness, incremental re-embedding.*
The **baseline** is what `pr-review-agent.html` §2.3 and §3.5 describe. The **upgrade** is what this matrix adds on top.

> **What you need to do in this file:** nothing to answer. Read it and push back on anything that looks wrong.
> Two choices are marked "Claude's suggestion". Change them if you disagree. Every term is in the glossary at the bottom.

---

## What this component is (read this first)

Before the reviewer can say "this change breaks the caller in `auth/session.py`", it needs to **find**
`auth/session.py`. This component prepares that. It reads every file in the repository, cuts each file into
pieces (**chunks**: one function, one class, or a block of lines), and stores each piece in two ways:
- as text, so we can search for an exact name like `verify_token` (that's group 3, keyword search);
- as an **embedding** (a list of numbers that captures what the code *means*), so we can find code that
  does something *similar* even when the names differ (group 3, vector search).

When the repository changes, it must update only what changed (**incremental refresh**), because turning
code into embeddings on your laptop's CPU takes minutes for a whole repo (decision S2).

## 1 · Purpose and contract

**Purpose.** Turn a repository at one commit into searchable chunks, each with an exact `path:start-end`
location, and keep them in step with the code at the lowest re-embedding cost.

**Contract.**
- **In:** a repository folder (or a git commit read via `git archive`), the repo name, the commit SHA.
- **Out:** rows in the SQLite file (decision S3): one per file (`path`, content hash, commit), one per chunk
  (`path`, `start_line`, `end_line`, `symbol`, text), plus the chunk's keyword-search entry and its vector.
- **Invariant:** every chunk's text is **exactly** lines `start..end` of that file at that commit. A finding
  that cites a chunk can then be checked line by line (the brief's grounding rule).
- **Not this component's job:** choosing what to retrieve for a PR (group 3).

## 2 · Assumptions (each one is a place it can break)

| # | Assumption | If it is false |
|---|---|---|
| A1 | Code can be cut into meaningful pieces | a function cut in half is useless context → I1, I2 |
| A2 | Everything in the repo is code worth indexing | binaries, generated and vendored files flood the index → I3 |
| A3 | Nothing in the repo is secret | a key in a `.env` file ends up in an LLM prompt → I4 |
| A4 | We can tell which files changed | stale chunks, or the whole repo re-embedded every time → I5, I6, I7 |
| A5 | All vectors in the index came from the same model | mixed vectors give meaningless similarity → I8 |
| A6 | An index run finishes | a half-written index looks complete → I9 |
| A7 | Line numbers are counted the same way everywhere | citations point at the wrong line → I12 |

## 3 · Failure modes

Each card says: what goes wrong · what we build · how we notice · what happens after.

**I1 · A chunk cuts a function in half.** *(quality · known-known)*
- **What goes wrong:** the html stores chunks by `(repo, path, chunk_index)` and doesn't say how files are cut. Cutting
  every N lines splits functions, so the reviewer sees the top half of a function without its `return`.
- **What we build:** Python files are cut along the code's structure using **AST** (the parse tree Python itself builds):
  one chunk per function, method or class body, plus one for the module-level lines. A function longer than 120 lines is
  split into overlapping windows that keep the function's name. Other files are cut into 60-line windows that overlap by 10.
- **How we notice:** a count of "functions split into windows".
- **What happens after:** context arrives whole. Long functions still arrive in labelled parts.

**I2 · A Python file doesn't parse.** *(engineering · known-known)*
- **What goes wrong:** a syntax error, or old Python 2 code, makes the AST step crash.
- **What we build:** fall back to line windows for that file only.
- **How we notice:** a "parse fallback" counter, with the file path.
- **What happens after:** the file is still searchable, just with coarser chunks.

**I3 · Junk floods the index.** *(cost + quality · known-known)*
- **What goes wrong:** images, lock files, minified JS, `node_modules`, `.venv` and huge generated files get chunked and
  embedded. That costs minutes and pushes real code out of the top results.
- **What we build:** skip rules: binary files (a zero byte in the first 8 KB), files over 200 KB, and known folders
  (`.git`, `node_modules`, `.venv`, `venv`, `dist`, `build`, `__pycache__`) and lock files.
- **How we notice:** a "skipped" count per reason.
- **What happens after:** nothing silently disappears; the skip list is in the run report.

**I4 · A secret gets indexed, and later sent to an LLM.** *(security · known-unknown)*
- **What goes wrong:** a `.env` file or a private key is chunked. Group 3 then puts it into a prompt sent to Groq.
- **What we build:** skip files by name (`.env*`, `*.pem`, `*.key`, `id_rsa*`), and skip any file containing a
  key-shaped string (a private-key header, an AWS `AKIA…` key ID, a GitHub `ghp_…` token).
- **How we notice:** a "skipped: possible secret" count. The log names the file, **never** the matched text (same rule as ingress F15).
- **What happens after:** that file can't be retrieved. A human sees the path in the report and decides.

**I5 · Changes are missed because "changed" is judged by time.** *(engineering · known-unknown)*
- **What goes wrong:** file timestamps change on checkout and stay the same on some copies, so "modified time" is unreliable.
- **What we build:** a **content hash** (SHA-256 of the file's bytes) per file. Same hash = unchanged.
- **How we notice:** the refresh report: files new / changed / unchanged / removed.
- **What happens after:** a refresh is exact and repeatable.

**I6 · Ghost chunks: old pieces stay after a file shrinks or is deleted.** *(quality · unknown-known)*
- **What goes wrong:** the html **upserts** chunks by `(repo, path, chunk_index)`. If a file had 12 chunks and now has 8,
  chunks 9-12 are never overwritten, so search keeps returning code that no longer exists. A deleted file keeps all of its chunks.
- **What we build:** a changed file's chunks are **replaced as a whole** in one transaction. Files missing from the new
  tree have their chunks removed from the index (rows in our SQLite file, not files on disk).
- **How we notice:** an invariant check: every chunk's path exists in the indexed tree.
- **What happens after:** search never cites code that isn't there.

**I7 · A one-line edit re-embeds the whole file.** *(cost · unknown-known)*
- **What goes wrong:** with chunks numbered by position, adding one line at the top shifts every chunk, so all of them
  look new and get re-embedded.
- **What we build:** vectors are cached by the **hash of the chunk's text**. A chunk whose text didn't change reuses its
  vector, wherever it moved in the file.
- **How we notice:** the refresh report: "chunks embedded" vs "vectors reused".
- **What happens after:** a small edit costs a few embeddings, not the whole file.

**I8 · Vectors from two different models get mixed.** *(quality · unknown-known)*
- **What goes wrong:** you switch from jina to the fallback model (S2). The old and new vectors don't share a meaning, so
  "similar" scores become noise, and nothing errors.
- **What we build:** the index records the model name and vector size. A run with a different model refuses to add to it
  and says a full rebuild is needed.
- **How we notice:** the refusal message.
- **What happens after:** you rebuild once; you never get silent nonsense.

**I9 · An index run crashes half-way.** *(operational · known-known)*
- **What goes wrong:** the laptop sleeps or the model runs out of memory after 300 of 900 files.
- **What we build:** each file is written in one transaction, and its hash is stored in that same transaction, last.
- **How we notice:** a run row with state `running` and no end time.
- **What happens after:** re-running continues: finished files match by hash and are skipped.

**I10 · Two index runs on the same repo at once.** *(engineering · known-known)*
- **What goes wrong:** both write chunks for the same file; the result depends on timing.
- **What we build:** one run per repo at a time, claimed with a UNIQUE row (the same trick as ingress F9).
- **How we notice:** the second run stops with "already running".
- **What happens after:** run it again when the first finishes.

**I11 · A file isn't valid UTF-8.** *(engineering · known-known)*
- **What goes wrong:** reading it raises an error and the run stops.
- **What we build:** bad bytes are replaced with a marker character, and the file is counted.
- **How we notice:** a "decode replaced" counter.
- **What happens after:** the run completes; that file's text may show markers.

**I12 · Line numbers drift.** *(quality · unknown-known)*
- **What goes wrong:** Windows line endings (CRLF), or a different line-splitting rule, make our line 40 differ from GitHub's line 40.
  A finding then cites the wrong line and fails grounding.
- **What we build:** one line-splitting rule used everywhere, and the invariant from section 1 checked over the whole repo in a test.
- **How we notice:** that test.
- **What happens after:** citations match what GitHub shows.

**I13 · Embedding is too slow on the laptop.** *(cost · known-unknown)*
- **What goes wrong:** jina on CPU may take seconds per batch; click is about 15,000 lines.
- **What we build:** batching; only new chunk texts are embedded (I7); the fallback model from S2 behind the same interface.
- **How we notice:** time per chunk in the run report.
- **What happens after:** if it's too slow, switch model (I8 forces the rebuild).
- **Claude's suggestion:** "too slow" = a full click index takes more than 10 minutes.

## 4 · Tests

| Test | What we do | Which failure | Pass means | Baseline should fail? |
|---|---|---|---|---|
| X1 | index the click repo; compare every chunk with the file's lines | I1, I12 | 100% of chunks match their lines exactly; no function split except the over-120-line ones | — (guards our code) |
| X2 | shrink a file from 12 chunks to 8, refresh | I6 | 0 stale chunks | **yes**: html upsert leaves 4 |
| X3 | delete a file, refresh | I6 | 0 chunks for it | **yes**: the upsert never removes |
| X4 | add one line at the top of a long file, refresh | I7 | 1–2 chunks embedded | **yes**: every chunk shifts |
| X5 | a repo with `.env`, a key file, a PNG, a lock file and `node_modules` | I3, I4 | none indexed; skip counts per reason; no secret text in any log | partly |
| X6 | change the model name, refresh | I8 | refused with "full rebuild needed" | yes |
| X7 | crash after N files, then re-run | I9 | completes; files done before the crash aren't redone | yes |
| X8 | a file with a syntax error and a file with invalid UTF-8 | I2, I11 | both indexed, both counted | yes |

The html baseline is rebuilt faithfully on SQLite for X2-X4 (60-line chunks numbered by position, upsert by
`(repo, path, chunk_index)`, re-embed when the file's hash changes). That's generous to it: the html doesn't say
how it detects change.

## 5 · Measured so far (25 Oct 2026, M5 part 1)

`python -m pr_review index-compare --tree eval/workdir/click-c69643b` → `eval/results/index_compare.json`.
The "before" is the html design rebuilt on SQLite (`ingestion/baseline.py`).

| Test | Right answer | html design | Ours |
|---|---|---|---|
| X2+X3 · stale chunks after one file shrinks (700 → 400 lines) and another disappears | 0 | 7 | 0 |
| X4 · embeddings after a one-line edit (plus the shrink and the rename above) | as few as possible | 13 | 2 |

All of X1 and X5–X8 pass in `pytest tests/index` (X1 runs over the whole click tree: every chunk is exactly its lines).
**Not measured yet:** I13 (speed of the real model), because the model can't be downloaded in Claude's workspace. That's
your step in `M5_START.md`. Until then the vector lane runs only with a test stand-in, and the numbers above don't depend on it.

## 6 · Glossary

| Term | Meaning |
|---|---|
| **Chunk** | one piece of a file that gets stored and searched: a function, a class, or a block of lines |
| **Embedding / vector** | a list of numbers (768 for jina) that captures what a piece of code means; similar code gets similar numbers |
| **AST** | Abstract Syntax Tree: the structure Python builds when it reads code (which lines are a function, a class, …) |
| **Incremental refresh** | updating the index for what changed only, not rebuilding it all |
| **Content hash / SHA-256** | a fingerprint of a file's bytes; same bytes give the same fingerprint |
| **Upsert** | "insert, or overwrite if the row already exists" |
| **Transaction** | a group of database writes that either all happen or none do |
| **CPU** | the laptop's main processor (no NVIDIA graphics card, so the model runs here) |
| **UTF-8** | the standard way of storing text as bytes |
| **CRLF** | the Windows line ending (two characters), vs LF on Linux/macOS |
| **SQLite / FTS5 / sqlite-vec** | our one database file (S3) / its built-in full-text search / an add-on for vector search |
