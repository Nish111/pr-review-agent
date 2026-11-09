# M9 · The live demo: two decisions, then setup

Written 7 Nov 2026. M9 is the last milestone: a real pull request on GitHub gets reviewed by our bot, live. Everything until now
ran on saved PRs on your laptop. M9 adds the parts that talk to GitHub, and you have to set up a few things only you can create
(they're tied to your GitHub account).

## What happens in the demo (end to end)

1. Someone opens a PR on a demo repository on GitHub.
2. GitHub sends a **webhook** (an automatic message) to our **GitHub App** (a bot identity you register on GitHub; it is what posts the comments).
3. The message reaches the receiver on your laptop (M4), which checks the signature and queues one review job.
4. The four specialists review it without code search (decision S6); the aggregator scores the comments (M7).
5. Comments scoring ≥ 0.84 are posted as a normal PR **comment** by the bot; the rest wait in `python -m pr_review queue` for you to approve.
   The bot never approves or merges (invariant), and a critical finding always waits for you.
6. `python -m pr_review trace` shows the whole review afterwards (M8).

## ★ D1 · Which repository does the demo run on?

| | What happens |
|---|---|
| **A · a new public demo repo with the notes-svc app (recommended)** | I prepare the files; you create an empty repo on GitHub (e.g. `notes-svc-demo`) and push them. The demo PR is one of our seeded PRs (S01, SQL injection: the bot's surest catch). Controlled, safe, and the result can be compared with the golden set, so the demo is also a check that the live path behaves like the evaluated one. |
| **B · your fork of pallets/click** | Real code, but our evaluation found nothing on real click PRs at the default setting (rung 4: nothing posts, everything queues). The demo would most likely show an approval queue, not the bot commenting. |
| **C · one of your own existing repos** | Realistic, but untested territory: no labels, so you can't tell whether a comment is right, and the bot would comment on real work. |
| **If you don't decide** | A. |

**Your answer (Nishant, 8 Nov 2026):** all three, in the order C, then B, then A.
**Claude's pushback, and what's applied:** one GitHub App can be installed on all three repos, so doing all three costs little extra. But
the **order** matters. Run **A first, as a 10-minute smoke test**, then C, then B as you said. On A we know what the right answer is (S01, the
SQL injection), so if anything goes wrong there it's our plumbing, not the reviewers. Starting on C, a wrong or missing comment could
be either, and you couldn't tell which. **Still needed from you: which repo is C** (name it in `M9_SETUP.md`, step 0).

## ★ D2 · How does GitHub reach your laptop?

GitHub can only send webhooks to a public internet address; your laptop doesn't have one. A relay solves that.

| | What happens |
|---|---|
| **A · smee.io (recommended)** | A free relay used in GitHub's own App tutorials: you open smee.io, get a URL, give it to the App, and run one command on your laptop that forwards messages to our receiver. No account, nothing installed globally (it runs with `npx`, which needs Node.js; check with `node --version`). Messages pass through smee's servers; they're signed by GitHub, and our receiver rejects anything with a bad signature (M4, F1). |
| **B · a Cloudflare quick tunnel (`cloudflared`)** | Also free, gives a public address straight to your laptop. Needs a program installed on Windows, and the address changes every time it starts, so the App's settings must be updated each time. |
| **C · no live webhook: replay a recorded one** | Works offline and is how the tests already run (M4), but it isn't a live demo, which is what M9 promises. |
| **If you don't decide** | A. |

**Your answer (Nishant, 8 Nov 2026):** A (smee.io).

## One thing I'll add, not a decision: a new dependency

A GitHub App proves who it is with a key you download from GitHub (a "private key"), and signing with it needs the `cryptography`
library; Python's standard library can't do it. So M9 adds the project's first required dependency besides the model libraries.
This time it goes into a **project venv** (a separate Python environment for this project), not your user-wide Python. That's the
lesson from M5, where installing into the shared Python upgraded `click` for every project.

## After you answer

I write `M9_SETUP.md` with every click and command for the option you chose (registering the App, its permissions, where the
key file goes, which secrets go where and how they stay out of git), and build the GitHub client and the live receiver meanwhile.
