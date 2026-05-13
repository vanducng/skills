# PR Title & Body Template

Canonical PR conventions — shared by `vd:git pr` and `vd:ship`. Both skills source title/body rules from this file so PRs read the same regardless of which one opened them.

## Body source — priority order

1. **Repo template wins.** If a PR template exists in the repo, fill it verbatim — do not append, do not reorder.
   ```bash
   for p in .github/pull_request_template.md .github/PULL_REQUEST_TEMPLATE.md docs/pull_request_template.md; do
     if [ -f "$p" ]; then cat "$p"; break; fi
   done
   ```
2. **Otherwise** use the fallback template below.

## Title

PR titles flip to **past tense (v-ed)** — they narrate what the branch did, not what to do. Commit messages stay imperative; only the PR title flips.

- **Length:** ≤ 70 chars
- **Ticket prefix in branch name** (regex `^([A-Z][A-Z0-9]+-[0-9]+)`):
  - Match → `<TICKET>: <v-ed description>` (e.g. `PRJ-123: added OAuth2 login`)
  - No match → `type(scope): <v-ed description>` (conventional-commit shape)
- **Types** (when no ticket): `feat` | `fix` | `refactor` | `perf` | `docs` | `test` | `chore` | `ci` | `build`
- **Scope:** dominant top-level changed dir

### Verb form

| Form | OK? | Example |
|---|---|---|
| Past tense (v-ed) | ✅ | `added OAuth2 login` |
| Imperative | ❌ | `add OAuth2 login` (commit form, not PR title) |
| Present-s | ❌ | `adds OAuth2 login` |
| Gerund | ❌ | `adding OAuth2 login` |

### Title examples

| Branch | Title |
|---|---|
| `PRJ-123-add-oauth` | `PRJ-123: added OAuth2 login flow` |
| `feature/oauth-cleanup` | `refactor(auth): consolidated OAuth helpers` |
| `fix/session-leak` | `fix(auth): closed session on logout` |
| `chore/bump-react` | `chore(deps): bumped react to 19.0` |

## Fallback body

Three labelled bullets + one verification stripe. No section headings — eliminates the Summary-vs-Changes overlap by construction. Same shape for 5-line fixes and 500-line features (the **What** bullet nests when needed).

```markdown
- **Why:** <one-sentence motivation>. <Closes #N / Relates to #M if any>
       _OR nested bullets when there are multiple distinct drivers (cap 4)_
- **What:** <semicolon-separated behavior shifts for ≤3 items, OR nested bullets for >3 (cap 7)>
- **Risks:** <breaking changes / migration notes — or `none`>

_Tests: <✓ N | ✗ N | – skipped> · Docs: <✓ | – N/A> · Breaking: <– | ⚠ see CHANGELOG>_
```

## Per-bullet fill rules

| Bullet | Source | Synthesis rule |
|--------|--------|----------------|
| **Why** | Top of `[Unreleased]` / `[X.Y.Z]` changelog entry → top commit body → branch name verbalized | Default: one sentence; drop low-signal verbs (`add`, `update`), promote the noun, end inline with `Closes #N`. Multiple distinct drivers (compliance + performance + UX) → nest as bullets. Hard cap 4 nested bullets; more means the PR has too many goals. |
| **What** | Commit subjects on the branch, deduped, grouped by behavioral domain | ≤3 items: semicolon-joined on one line. >3: nested bullets. Each item is a *behavior change*, not a file change. Reject "renamed file X" — keep "renamed cookie from `sid` to `__Host-session`". Hard cap 7 nested bullets — more is a scope smell. |
| **Risks** | Breaking-change scan on diff: removed exports, schema migrations, env var changes, removed CLI flags, `BREAKING CHANGE:` in commit body | Lead with severity word: `Breaking — …` / `Migration — …` / `none`. Keep `none` explicit; never omit the bullet. |
| **Verification** | Live `gh pr checks` output for tests; `docs/` files in diff for Docs; same breaking-change scan for Breaking | One italic stripe. Regenerate after CI reports green so reviewers see live status, not commit-time snapshot. |

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

**PR with multiple motivations (nested Why):**

```markdown
- **Why:**
  - legal flagged session-token storage as non-compliant with new requirements (deadline 2026-06-01)
  - existing middleware leaks request context across goroutines under load (#84)
  - moving to OAuth lets us drop the home-rolled crypto and 600 lines of auth code
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

## Hard rules

- **Repo template, when present, is law** — do not append, do not reorder. Just fill.
- **Issue closers (`Closes #42`)** live inline in the **Why** bullet — no separate Linked-Issues section.
- **Verification stripe values** come from live tooling output, never the author's claim.
- **Existing PR for this branch** → `gh pr edit`, never re-create.
- **Beta PRs** target dev/beta branch, not main.
- **No AI attribution** in title or body. No "Generated with Claude" / `Co-Authored-By: Claude` / emoji unless explicitly asked.
- **`gh pr create --fill`** uses commit messages directly (imperative). After `--fill`, re-edit the title with `gh pr edit --title "<v-ed title>"` to flip it to past tense.
