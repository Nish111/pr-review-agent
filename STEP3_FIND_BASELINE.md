# OSPREY session 1 · Step 3 · Find the supplied baseline

Written 18 Oct 2026. This is the one thing you need to do before step 4 (component list + first failure matrix).

## What is already settled (no action)

- **Step 1 done.** This chat now has access to `D:\Nishant\Learnings_NewLaptop\Antern\`.
- **Step 2 done, and no download was needed.** `Antern\Session15-16\pr-review-agent.html` was already on
  disk (125 KB, full text). The NEEDS_MANUAL_DOWNLOAD row 20 entry is out of date.
- **What the html turned out to be:** the full *design* the lecture derived — 20-phase build roadmap, a
  23-module "modular monolith" map (FastAPI + Redis/ARQ + LangGraph + 4 specialist agents + aggregator +
  HITL gate, Tiger Cloud / pgvectorscale as the one data store), ADR-002 and ADR-003 named.
  It says *"This is the exact code we will build"* but contains **no code and no repo link.**
  So the html is the baseline **architecture and decisions**; the baseline **code** is still missing.

## The one lead

In the Saturday 18 Jul lecture chat (`Antern\Session15-16\chatSat18-7-2026.txt`, 19:13:41) Ayush posted:

    https://drive.google.com/drive/folders/1Oa8mPXuI9SI7DeBqnfMySjb0eJy8XkfN?usp=sharing

On Discord (#daily-progress, 25 Jul) it was re-shared as the answer to "were the AI PR review system
designs Ayush presented uploaded?". The folder's title is **AI-PR-REVIEW-AGENT-RECORDINGS** — so it is
probably recordings, but it may also hold the code. I could not open it (Chrome extension not connected
from this chat; Drive needs your sign-in).

## Your steps

1. Open the link above in your browser while signed in.
2. Write below, under "What I found", every file name you see in it (and in any sub-folder).
3. If you see anything that looks like code (a `.zip`, a folder named `backend`, `pr-review-agent`, a
   GitHub link in a doc): download it into `D:\Nishant\Learnings_NewLaptop\Antern\Session15-16\baseline\`.
   Don't unzip — I'll do it.
4. Say "step 3 done" in the OSPREY chat.

## If the folder has only recordings (the likelier case)

Then there is no supplied code baseline that we can find, and the honest reading of the brief is:
**the html IS the supplied baseline** (architecture, decisions, constraints) and "ingest before you
implement" means ingesting the html + brief into Genesis. Paste this in #questions-for-ayush to confirm:

> For the W8 PR Review Agent brief, §1 says "start from the supplied baseline … architecture, code,
> decisions". Is there a baseline repo/code we should start from, or is pr-review-agent.html (the design
> + module map) the baseline, and we build the single-LLM reviewer ourselves as step 1 of the improvement story?

## What I found
<!-- TODO (Nishant): list the folder contents here -->
Added a doc "PR Agent doc" which covers the first video, also added screenshots and notes in my words

## Outcome (Claude, 19 Oct)

- The Drive folder is **10 lecture videos, no code**: 1 overview, 4 on the PR-agent template, 5 of the
  instructor building it. Your notes on video 1 are in `PR Agent Doc.docx`.
- So there's **no supplied code baseline**. The baseline = the design in `pr-review-agent.html` (roadmap,
  module map, ADR-001/002/003) + what the instructor builds in videos 6-10. Your note on the last
  screenshot says the same: "this is the roadmap and baseline, what u build is on top of this".
- The Discord question to Ayush is now **optional** (only if videos 6-10 show code that isn't shared).
- Step 3 is closed. Step 4 part 1 (component list) is in `COMPONENT_LIST.md`.
