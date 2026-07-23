# PR Body & Title (ship-specific)

Used by Step 12 (`gh pr create` / `gh pr edit`) and refreshed by Step 14 once CI reports green.

## Canonical conventions live elsewhere

**Title format, body shape, per-bullet fill rules, and worked examples** are owned by `vd:git`'s canonical PR template:

> `~/skills/skills/git/references/pr-template.md`

Load that file for: past-tense (v-ed) titles, ticket-prefix detection, repo-template detection, fallback Why / What / Risks + verification block, examples.

## Ship-specific integration

| Step | What this skill adds beyond the canonical template |
|---|---|
| **Step 12 — Create PR** | Resolve title + body via the canonical rules. Existing PR for this branch → `gh pr edit`. |
| **Step 12 — Inline issue refs** | `Closes #N` / `Relates to #M` from Step 2 go inline in the **Why** bullet — no separate Linked-Issues section. |
| **Step 14 — Verification block refresh** | After CI watch reports green, regenerate the three-line verification block (`**Tests:** …` / `**Docs:** …` / `**Breaking:** …`, one field per line) so reviewers see live status, not commit-time snapshot. |
| **Beta channel** | Beta PRs target `dev` / `beta` branch, not `main`. Title and body shape are unchanged. |
| **No AI attribution** | Never add `Co-Authored-By: Claude`, "Generated with Claude", or a `https://claude.ai/code/session_...` session link to the PR title, body, or any PR comment ship posts. |
