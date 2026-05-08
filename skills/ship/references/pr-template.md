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

Three labelled bullets + one verification stripe. No section headings — eliminates the Summary-vs-Changes overlap by construction. Same shape for 5-line fixes and 500-line features (the **What** bullet nests when needed).

```markdown
- **Why:** <one-sentence motivation>. <Closes #N / Relates to #M if any>
- **What:** <semicolon-separated behavior shifts for ≤3 items, OR nested bullets for >3>
- **Risks:** <breaking changes / migration notes — or `none`>

_Tests: <✓ N | ✗ N | – skipped> · Docs: <✓ | – N/A> · Breaking: <– | ⚠ see CHANGELOG>_
```

## Per-bullet fill rules

| Bullet | Source | Synthesis rule |
|--------|--------|----------------|
| **Why** | Top of `[Unreleased]` / `[X.Y.Z]` changelog entry → top commit body → branch name verbalized | One sentence. Drop low-signal verbs (`add`, `update`); promote the noun. End inline with `Closes #N` if any. |
| **What** | Commit subjects on the branch, deduped, grouped by behavioral domain | ≤3 items: semicolon-joined on one line. >3: nested bullets. Each item is a *behavior change*, not a file change. Reject "renamed file X" — keep "renamed cookie from `sid` to `__Host-session`". Hard cap 7 nested bullets — more is a scope smell. |
| **Risks** | Breaking-change scan on diff: removed exports, schema migrations, env var changes, removed CLI flags, `BREAKING CHANGE:` in commit body | Lead with severity word: `Breaking — …` / `Migration — …` / `none`. Keep `none` explicit; never omit the bullet. |
| **Verification** | Live `gh pr checks` output for tests; `docs/` files in diff for Docs; same breaking-change scan for Breaking | One italic stripe. Regenerated after Step 14 (CI watch) reports green so reviewers see live status, not commit-time snapshot. |

## Rules

- Repo template, when present, is law — do not append, do not reorder. Just fill.
- Issue closers (`Closes #42`) live inline in the **Why** bullet — no separate Linked-Issues section.
- Verification stripe values come from live tooling output, never the author's claim.
- Existing PR for this branch → `gh pr edit`, never re-create.
- Beta PRs target dev/beta branch, not main.

## Title examples

Branch `PRJ-123-add-oauth` → `PRJ-123: added OAuth2 login flow`
Branch `feature/oauth-cleanup` → `refactor(auth): consolidated OAuth helpers`
Branch `fix/session-leak` → `fix(auth): closed session on logout`

## Body examples

**Tiny PR (typo fix):**

```markdown
- **Why:** Fix typo in OAuth provider error message that confused users.
- **What:** corrected `Authentcation failed` → `Authentication failed` in `src/auth/errors.ts`.
- **Risks:** none.

_Tests: ✓ 127 · Docs: – N/A · Breaking: –_
```

**Mid-sized PR (≤3 behavior shifts):**

```markdown
- **Why:** Replace home-rolled session middleware with OAuth2 for security + standards compliance. Closes #42.
- **What:** login redirects to provider OAuth flow; old `/api/login` removed; session cookie renamed to `__Host-session` with Secure+HttpOnly.
- **Risks:** Breaking — existing sessions invalidated on deploy. Documented in CHANGELOG.

_Tests: ✓ 127 · Docs: ✓ · Breaking: ⚠_
```

**Large PR (>3 shifts, nested What):**

```markdown
- **Why:** Replace home-rolled session middleware with OAuth2 (Google + GitHub) for security + standards compliance. Closes #42.
- **What:**
  - login redirects to provider OAuth flow; old `/api/login` removed
  - session cookie renamed `sid` → `__Host-session`; Secure + HttpOnly
  - logout now revokes the provider token, not just the local cookie
  - server fails fast at startup if `OAUTH_GOOGLE_*` / `OAUTH_GITHUB_*` env vars are missing
- **Risks:** Breaking — existing sessions invalidated on deploy. Migration: clients must re-authenticate. Documented in CHANGELOG.

_Tests: ✓ 412 · Docs: ✓ · Breaking: ⚠ see CHANGELOG_
```
