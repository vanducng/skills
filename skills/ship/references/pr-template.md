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

```markdown
## Summary
<bullets — from changelog / commits>

## Linked Issues
- Closes #XX — <title>
<or "No linked issues.">

## Pre-Landing Review
<X critical, Y informational> — or "No issues found."
<list informational findings as `[file:line] note`>

## Test Results
- [x] All tests pass (<count>, 0 failures)
<or `- [x] Tests skipped (--skip-tests)`>

## Changes
<git diff --stat, top files>

## Ship Mode
- Mode: <official|staging|beta|release>
- Target: <target-branch>
```

## Rules

- Repo template, when present, is law — do not append, do not reorder. Just fill.
- Always include linked-issues line; write "No linked issues." when empty.
- Always include the review line, even when clean — proves review ran.
- Test counts come from `tester` agent output, not estimates.
- Existing PR for this branch → `gh pr edit`, never re-create.
- Beta PRs target dev/beta branch, not main.

## Examples

Branch `PRJ-123-add-oauth` → `PRJ-123: added OAuth2 login flow`
Branch `feature/oauth-cleanup` → `refactor(auth): consolidated OAuth helpers`
Branch `fix/session-leak` → `fix(auth): closed session on logout`
