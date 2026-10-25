# M5 · Your one step: check the embedding model runs on your laptop

Written 25 Oct 2026.

## What M5 is, and why this step comes first

M5 builds the code index (matrix 02) and the search over it (matrix 03): the part that lets the reviewer see code
**outside** the diff, such as the other places that call a function the PR changed.

Search has two halves. The **keyword** half (exact names like `verify_token`) is built into Python's SQLite, so it
needs nothing from you. The **vector** half ("code that means something similar") needs:
- an **embedding model** that runs on your CPU (decision S2), and
- **sqlite-vec**, a small add-on that lets SQLite store and search vectors (decision S3).

I can't test either here: my workspace is blocked from downloading models from Hugging Face (the site that hosts
them). So S2 says "confirm it installs and runs at the start of M5", and only your laptop can do that.
While you do this, I'm building everything that doesn't depend on the answer. If the model turns out too slow or
won't run, the system runs keyword-only and says so (matrix 03, R8), so nothing is blocked either way.

## One decision first: may the jina model run its own code?

`jina-embeddings-v2-base-code` (our first choice in S2: trained on code) only loads with `trust_remote_code=True`.
That means Python downloads and runs a small code file from the `jinaai` page on Hugging Face, not just the model's numbers.
`bge-small` (the S2 fallback: trained on English text, not code) needs no such code.

| | What happens |
|---|---|
| **A · allow jina (recommended)** | Better "similar code" results, because it was trained on code. The spike prints the exact version it downloaded, and I pin that version, so the downloaded code can't change under us later. Risk: you run code from Jina AI's page once per download (a well-known company and model, but it's still downloaded code). |
| **B · don't allow** | Nothing downloaded is run, only bge-small's numbers. The vector lane is weaker on code. Exact-name search, the half that matters most for review, is unaffected. |
| **Not deciding** | I treat it as B: run only bge-small. You can switch to A later, but switching models forces a full re-index (matrix 02, I8), which takes a few minutes. |

## The step

Run these from the `10-PR-Review-Agent` folder, in the same Python you use for `pytest`.

**1. Install the two add-ons** (one time; downloads roughly 1 GB, most of it PyTorch, the library that runs the model):
```
python -m pip install sentence-transformers sqlite-vec
```

**2a. If you chose A:**
```
python eval/spikes/s2_embed_check.py --allow-jina
```
**2b. If you chose B, or haven't decided:**
```
python eval/spikes/s2_embed_check.py
```
The first run downloads each model (about 130 MB for bge-small, 300 MB for jina), so it can take a few minutes.

**3. Paste the whole printed output into the chat**, and say A or B.

## What I'll read in the output

| Line | What it tells me |
|---|---|
| `sqlite-vec  ok …` | the vector store works in your Python. `FAILED` → keyword-only mode for now, and I look for a fix |
| `seconds per chunk` / `est. click index (min)` | under 10 minutes = fine (matrix 02, I13). Over → we use bge-small, or index only the folders the PRs touch |
| `similar vs unrelated` | a sanity check that the model understands code: the first number should be clearly higher |
| `revision (pin this)` | the exact model version, which I write into S2 so every run uses the same one |
| any `FAILED` | paste it anyway; it tells me what to fix |
