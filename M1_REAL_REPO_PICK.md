# M1 · Pick the public repo for the 6 real PRs

Written 21 Oct 2026. M0 is committed (`abf09b2`, from your `Temp10.md` paste).

## What we're doing and why

The golden set (decision `.genesis/decisions/S4-golden-pr-source.md`) needs **~6 real merged PRs**, each linked
to a real GitHub issue, so their "right answer" comes from the project's own tracker. They all come from **one**
public Python repo, because the reviewer has to index that repo's code (milestone M5) to review its PRs properly.

**What makes a repo suitable:**
1. **Python**, so our tools and code search work on it;
2. **small to mid size**, so indexing it on your laptop's processor takes minutes, not hours (`S2-embedding-model.md`);
3. **permissive licence** (BSD / MIT / Apache), so we can copy diffs into our repo as test data;
4. **disciplined issue tracking**: bug issues that name the PR that caused or fixed them;
5. **readable to you**, because you judge each label.

## ⚠ Source check: I could NOT verify these myself

GitHub's API isn't enabled for this session, and opening GitHub pages needed your approval, which timed out.
So the three candidates below come from **my general knowledge, not checked today**. Your step is the check.

| Candidate | Why it's on the list (unverified) | Check here |
|---|---|---|
| **pallets/click** | Python CLI library; BSD-3; known for tidy issues and changelog entries that name issue numbers | https://github.com/pallets/click/issues?q=is%3Aissue+is%3Aclosed+label%3Abug |
| **encode/httpx** | Python HTTP client; BSD-3; mid-size | https://github.com/encode/httpx/issues?q=is%3Aissue+is%3Aclosed |
| **jd/tenacity** | Python retry library; Apache-2.0; small, so fast to index, but fewer bugs to choose from | https://github.com/jd/tenacity/issues?q=is%3Aissue+is%3Aclosed |

## Your one step

1. Open each "Check here" link while signed in to GitHub.
2. For each repo, write below: **(a)** roughly how many closed bug issues there are, and **(b)** whether you can open 2 of them and find the PR they link to (yes / no).
3. Pick one.

- click:
- httpx:
- tenacity:
- **My pick:**

**Recommendation: click**, if your check confirms it has plenty of closed bug issues with linked PRs.
- **If you follow it:** mid-size code, clean issue history, and a CLI library is easy to reason about when you label PRs.
- **If you pick httpx:** also fine; more network-related code, so the security specialist gets more to look at, but labels take more thought.
- **If you pick tenacity:** fastest to index, but it may not have 6 good issue-linked bugs.
- **If you don't decide:** M1 builds the 14 seeded PRs first (they don't depend on this), and the real 6 wait.

## While you check

I'll write the **core data shapes** (`Finding`, `Review`, `Job`) and their tests, in `src/pr_review/contracts/`.
That's deterministic work with nothing for you to decide; you'll get the commit commands with it.

## Glossary

| Term | Meaning |
|---|---|
| **Golden set** | PRs where the right review is known in advance; the yardstick for every version |
| **Issue-linked PR** | a GitHub issue (e.g. a bug report) that names the PR which caused or fixed it |
| **Licence (BSD / MIT / Apache)** | permissive open-source licences that allow copying code with attribution |
| **Index (M5)** | turning a repo's code into searchable pieces so the reviewer can find related code |
