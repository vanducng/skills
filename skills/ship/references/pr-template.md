# PR Body & Title

Used by Step 12 (`gh pr create` / `gh pr edit`).

## Body source — priority order

1. **Repo template wins.** If `.github/pull_request_template.md` (or `.github/PULL_REQUEST_TEMPLATE.md`) exists, use it verbatim and fill its sections from ship context.
2. **Otherwise** use the fallback template below.

```bash
for p in .github/pull_request_template.md .github/PULL_REQUEST_TEMPLATE.md docs/pull_request_template.md; do
  if [ -f "$p" ]; then cat "$p"; break; fi
done
```

## Title

- Detect ticket prefix in branch name: regex `^([A-Z][A-Z0-9]+-[0-9]+)`
  - Match → title = `<TICKET>: <brief description>` (e.g. `PRJ-123: added OAuth2 login`)
  - No match → title = `type(scope): <brief description>` (conventional commit style)
- Description: past tense (v-ed), ≤ 70 chars, infer from commits / changelog entry.
  - Examples: `added OAuth2 login`, `fixed auth session leak`, `refactored billing module`.
  - Not: `add OAuth2 login` (imperative) or `adds OAuth1 login` (present-s).
- Type (when no ticket): `feat` | `fix` | `refactor` | `perf` | `docs` | `test` | `chore`.
- Scope: dominant top-level changed dir.

## Fallback body template

Lean by design — reviewers should grasp the PR in 30 seconds. Drop sections that don't help them decide.

```markdown
## Summary
<2-4 sentences synthesizing the change from commits + diff. Lead with *why*, then *what*. End with `Closes #XX` / `Relates to #YY` inline if there are issues. No bullets here — prose. If beta/staging, mention the target audience.>

## Changes
- <high-level bullet of a major change>
- <another major change>
<3-7 bullets max — describe behavior shifts, not file lists. Skip the diff-stat dump.>

## Checklist
- [x] Tests pass (<count>) <or `[x] Tests skipped (--skip-tests)`>
- [x] No breaking changes <or `[ ] Breaking changes documented in CHANGELOG`>
- [x] Docs updated <or `[x] N/A`>
```

**Rules for the fallback:**
- Summary is prose, not bullets — forces synthesis. If you can't write 2-4 sentences explaining the PR, the scope is wrong.
- Issue links (`Closes #42`) belong inside Summary, not a separate section — keeps the body lean and gives reviewers context next to the *why*.
- Changes lists *behaviors that changed*, not files that changed. `git diff --stat` is one click away in the PR view; don't paste it.
- Drop the Pre-Landing Review and Ship Mode sections — review findings live in the conversation, mode is visible from base/head branches.
- Cap at ~25 lines of body. Big PR? That's a scope smell, not a template problem.

## Rules

- Repo template, when present, is law — do not append, do not reorder. Just fill.
- Inline issue closers (`Closes #42`) inside the Summary paragraph; no separate "Linked Issues" section.
- Test counts come from `tester` agent output, not estimates.
- Existing PR for this branch → `gh pr edit`, never re-create.
- Beta PRs target dev/beta branch, not main.

## Title examples

Branch `PRJ-123-add-oauth` → `PRJ-123: added OAuth2 login flow`
Branch `feature/oauth-cleanup` → `refactor(auth): consolidated OAuth helpers`
Branch `fix/session-leak` → `fix(auth): closed session on logout`

## Body example

```markdown
## Summary
Replaces the home-rolled session middleware with Google + GitHub OAuth2.
Sessions now use signed, encrypted cookies (HMAC + AES-GCM) and expire
after 24h instead of staying alive until manual logout. Closes #42.

## Changes
- Login route now redirects to provider OAuth flow; old `/api/login` removed.
- Session cookie name changed from `sid` to `__Host-session`; Secure + HttpOnly.
- Server reads `OAUTH_GOOGLE_*` / `OAUTH_GITHUB_*` env vars at startup; missing → fail-fast.
- Logout endpoint revokes the provider token, not just the local cookie.

## Checklist
- [x] Tests pass (127)
- [x] Breaking change: existing sessions invalidated on deploy — noted in CHANGELOG
- [x] Docs updated
```
