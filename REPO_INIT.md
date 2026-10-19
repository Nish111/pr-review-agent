# Step: create the PR Review Agent repo and lay the Genesis spine

**Written 19 Oct 2026.** The brief's first deliverable is "a Genesis-managed repository"
(`LMS_Archive/docs/week-8-pr-review-agent-build.md` §1, §4.1). Nothing here needs thinking except
the one decision below. Everything else is fixed commands with a check after each.

---

## Decision (the only one): where the repo lives

<!-- UPDATE: write A or B on the line below. Direction if unsure: A. -->
**Choice:**

| Option | If chosen | If not chosen |
|---|---|---|
| **A · This folder (`10-PR-Review-Agent`) becomes the repo** | The design work already done (component list, ingress failure matrix v3, handoff) is the first commit, which is exactly the "prior context" the brief says Genesis must ingest. One place for everything. `.gitignore` (already written) keeps `PR Agent Doc.docx` out because it's a 1 MB binary. | Plans and code end up in two folders and have to be kept in sync by hand. |
| **B · A new sibling folder `11-pr-review-agent`** | A clean repo with code only. The planning files stay outside git, so the "how it was derived" story has no history. | — |
| **Not deciding** | — | Nothing can be scaffolded, and the PR agent stays at step 3 of the brief. |

The commands below assume **A**. For B, replace the `cd` path and run `mkdir` first.

---

## Commands (Git Bash, in order). Paste all output into `Temporary.md`

*(Checked by Claude, 19 Oct: the Genesis kit path, the scaffold flags and the model names match what the incident-memory repo used. One fix: step 2 used `git add *.md`, which would fail once `Temporary.md` exists, because it's ignored. It now uses `git add .`.)*

```bash
# 0 · prerequisites: node must be v18 or newer (graphizer needs it)
git --version
node --version

# 1 · make the folder a repo
cd "/d/Nishant/Learnings_NewLaptop/Claude/AI-Sprint-Execution/10-PR-Review-Agent"
git init -b main
git status --short            # check: the .md files + .gitignore listed, NO .docx

# 2 · first commit = the prior context, before Genesis touches anything
git add .                     # adds everything not excluded by .gitignore (so Temporary.md and the .docx stay out)
git status --short            # check again: still no .docx, no Temporary.md
git commit -m "PR Review Agent: prior context before Genesis (component list, ingress failure matrix v3, handoff)"

# 3 · lay the Genesis spine (flags given so there are no prompts; same values as incident-memory)
KIT="/d/Nishant/Learnings_NewLaptop/Claude/AI-Sprint-Execution/03-Week3-Offer-And-Audits/Genesis/genesis-kit-main/genesis-kit-main"
bash "$KIT/tools/scaffold.sh" . pr-review-agent \
  --cheap-model claude-haiku-4-5 --flagship-model claude-opus-4-5 \
  --router-skill coding-orchestrator --budget 50000 --max-iters 10
node "$KIT/tools/graphizer.mjs" . --write
ls -la .genesis                # check: CURRENT is under checkpoints/, plus PLAN.md, DONE.html, LOOPS.md, context-graph.json

# 4 · commit the empty spine on its own (so the ritual's edits show as a diff against the template)
git add .genesis
git commit -m "Genesis scaffold for pr-review-agent (genesis-kit, unfilled)"

# 5 · GitHub: create an EMPTY repo named pr-review-agent at https://github.com/new
#     (no README, no .gitignore, no licence; private is fine for now). Then:
git remote add origin git@github.com:Nish111/pr-review-agent.git
git push -u origin main
git log --oneline              # check: exactly 2 commits
```

**Done when:** `git log --oneline` shows 2 commits, `.genesis/` exists, and the push succeeded.

## What comes next (not now)

The Genesis ritual G0–G6. This is the part that needs thinking: the 5 diagnostic questions (scope
is **extend**, because the baseline design exists), invariants, definition of done, and milestones
that each have one demo command. I'll prepare it as a file with your choices marked, the same as
the incident-memory kickoff interview.
