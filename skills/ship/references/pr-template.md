# PR Body & Title (ship-specific)

Used by Step 12 (`gh pr create` / `gh pr edit`) and refreshed by Step 15 once CI reports green.

## Canonical conventions live elsewhere

**Title format, body shape, per-bullet fill rules, and worked examples** are owned by `vd:git`'s canonical PR template:

> `../git/references/pr-template.md` (sibling git skill, resolved from the skill root)

Load that file for: past-tense (v-ed) titles, confirmed-ticket selection, repo-template detection, fallback Why / What / Risks + verification block, examples.

## Ship-specific integration

| Step | What this skill adds beyond the canonical template |
|---|---|
| **Step 12 - Create PR** | Resolve title + body via the canonical rules. Existing PR for this branch → `gh pr edit`. |
| **Step 12 - Inline issue refs** | `Closes #N` / `Relates to #M` from Step 2 go inline in the **Why** bullet - no separate Linked-Issues section. |
| **Step 15 - Verification block refresh** | After CI watch reports green, regenerate the three-line verification block (`**Tests:** …` / `**Docs:** …` / `**Breaking:** …`, one field per line) so reviewers see live status, not commit-time snapshot. |
| **Beta channel** | Beta PRs target `dev` / `beta` branch, not `main`. Title and body shape are unchanged. |
| **No AI attribution** | Never add `Co-Authored-By: Claude`, "Generated with Claude", or a `https://claude.ai/code/session_...` session link to the PR title, body, or any PR comment ship posts. |
| **Step 12 - Screenshot marker** | For user-visible changes, draft the body with a `<!-- SCREENSHOTS -->` marker after the verification block. Step 12b substitutes the HTML table. |
| **Step 12b - Before/after** | **Expected for UI-visible diffs** (not a merge gate). Capture or reuse a before/after pair, upload via `gh_upload_image`, embed in the PR, and mirror onto the confirmed ticket. Full recipe: `before-after.md`. Upload mechanics: `../git/references/gh-cli-guide.md` → *Attach screenshots*. Skip with `--skip-screenshots` or when capture is impossible - say why once. |

## Before/after evidence (user-visible changes)

**Expected when the diff changes what a user sees. Never blocks the ship.** Skip for
non-visual changes, `--skip-screenshots`, unknown URLs, or when driving the UI would
cost more than the evidence is worth - say so once and move on.

When it is cheap - captures already taken during cook/fix, or two reachable URLs - a
before/after pair beats a paragraph. Capture **the same page, viewport, and scroll
position** in both shots so only the change differs; a mismatched pair is worse than
none.

What to capture, by change type:

| Change | Before | After |
|---|---|---|
| New/changed control | Current prod or `main` build | This PR's preview build |
| New guard or validation | Action attempted, no guard | Guard firing, plus the success path once satisfied |
| Bug fix | The broken state reproduced | Same steps, correct behaviour |

Pair each shot with the observed value (row count, error text, ID) in the surrounding
table - the image shows it happened, the number makes it checkable.

Procedures (capture CLIs, GitHub upload, Jira inline): `before-after.md`.
Do **not** commit review screenshots to the repo; they are ephemeral evidence, not
documentation. Do **not** use public paste hosts (`0x0.st`, etc.) for private work.
