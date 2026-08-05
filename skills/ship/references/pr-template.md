# PR Body & Title (ship-specific)

Used by Step 12 (`gh pr create` / `gh pr edit`) and refreshed by Step 14 once CI reports green.

## Canonical conventions live elsewhere

**Title format, body shape, per-bullet fill rules, and worked examples** are owned by `vd:git`'s canonical PR template:

> `~/skills/skills/git/references/pr-template.md`

Load that file for: past-tense (v-ed) titles, ticket-prefix detection, repo-template detection, fallback Why / What / Risks + verification block, examples.

## Ship-specific integration

| Step | What this skill adds beyond the canonical template |
|---|---|
| **Step 12 - Create PR** | Resolve title + body via the canonical rules. Existing PR for this branch → `gh pr edit`. |
| **Step 12 - Inline issue refs** | `Closes #N` / `Relates to #M` from Step 2 go inline in the **Why** bullet - no separate Linked-Issues section. |
| **Step 14 - Verification block refresh** | After CI watch reports green, regenerate the three-line verification block (`**Tests:** …` / `**Docs:** …` / `**Breaking:** …`, one field per line) so reviewers see live status, not commit-time snapshot. |
| **Beta channel** | Beta PRs target `dev` / `beta` branch, not `main`. Title and body shape are unchanged. |
| **No AI attribution** | Never add `Co-Authored-By: Claude`, "Generated with Claude", or a `https://claude.ai/code/session_...` session link to the PR title, body, or any PR comment ship posts. |
| **Step 12 - Screenshot evidence** | **Optional.** For user-visible changes, if captures already exist, draft the body with a `<!-- SCREENSHOTS -->` marker and substitute them in. Recipe: `~/skills/skills/git/references/gh-cli-guide.md` → *Attach screenshots*. |

## Screenshot evidence (optional, UI-visible changes)

**Never blocks the ship.** Skip it for non-visual changes, when no captures exist, or when driving
the UI would cost more than the evidence is worth - say so in the verification block and move on.
Do not stall a PR hunting for a screenshot.

When it is cheap - captures already taken during verification - a before/after pair beats a
paragraph. Capture **the same page, viewport, and scroll position** in both shots so only the change
differs; a mismatched pair is worse than none, because the reviewer cannot tell what is signal.

What to capture, by change type:

| Change | Before | After |
|---|---|---|
| New/changed control | Current prod or `main` build | This PR's preview build |
| New guard or validation | Action attempted, no guard | Guard firing, plus the success path once satisfied |
| Bug fix | The broken state reproduced | Same steps, correct behaviour |

Pair each shot with the observed value (row count, error text, ID) in the surrounding table - the
image shows it happened, the number makes it checkable.

Upload mechanics, private-repo constraints, and verification are in
`~/skills/skills/git/references/gh-cli-guide.md`. Do **not** commit review screenshots to the repo;
they are ephemeral evidence, not documentation.
