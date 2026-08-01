# PR Title & Body Template

Canonical PR conventions - shared by `vd:git pr` and `vd:ship`. Both skills source title/body rules from this file so PRs read the same regardless of which one opened them.

## Body source - priority order

1. **Repo template wins.** If a PR template exists in the repo, fill it verbatim - do not append, do not reorder.
   ```bash
   for p in .github/pull_request_template.md .github/PULL_REQUEST_TEMPLATE.md docs/pull_request_template.md; do
     if [ -f "$p" ]; then cat "$p"; break; fi
   done
   ```
2. **Otherwise** use the fallback template below.

## Body transport and verification

Send Markdown through `--body-file -`; never pass escaped newlines through
`--body`. The quoted heredoc preserves real line breaks and prevents shell
expansion.

```bash
gh pr create --title "<title>" --body-file - <<'EOF'
<markdown body>
EOF

gh pr edit <number> --body-file - <<'EOF'
<markdown body>
EOF
```

After every create or edit, fail if GitHub stored literal `\n` sequences:

```bash
if gh pr view <number> --json body --jq .body | grep -Fq '\n'; then
  echo 'PR body contains literal \n sequences' >&2
  exit 1
fi
```

## Brevity rules (applies to both repo-template and fallback)

PR readers have the diff one click away. Body explains *why* and *what's risky*, not *what changed line-by-line*. **A reviewer should scan the body in 10 seconds and decide whether to dive into the diff.**

| Section | Length |
|---|---|
| **Why / Context** | 1–2 sentences. Motivation + ticket. No RCA, no scout reports, no narrative. |
| **Main Changes / What** | 3–5 bullets max. Each bullet = a behavior or surface change, not a file list. Stop describing once a curious reader could open the diff and see the rest. |
| **Notes / Additional Notes** | Optional. Only add a note if a reviewer genuinely needs it (sequencing, breaking change, manual deploy step, follow-up flagged). If nothing surprising, omit or write `none`. |
| **Checklist** | Tick honestly. Don't pad with explanations. |

These section *names* are conceptual - they map onto whichever body shape the repo uses. The **repo-template** path keeps the heading style (`## Context`, `## Main Changes`, `## Additional Notes`, `## Checklist`). The **fallback body** path collapses them into labelled bullets: `Why` = Context, `What` = Main Changes, `Risks` = Notes, and the verification block replaces Checklist. Don't introduce both styles in one PR.

### Anti-patterns

- ❌ Listing every file touched ("Created `models/observability/cnb_obs_dbt_test_runs.sql`, created `models/observability/cnb_obs_dbt_invocations.sql`, ...") - group instead: "5 dbt views + 1 incremental snapshot under `models/observability/`."
- ❌ Re-stating the diff in prose ("This PR builds on top of elementary which already populates run results...")
- ❌ Multi-paragraph "Context" sections that recap scouting / brainstorming. That belongs in Jira / the plan file.
- ❌ Marketing language ("Foundation for future tickets", "comprehensive solution").
- ❌ Repeating commit-message content. The commit is already in the PR; don't duplicate it in the body.

### Too long vs right

**Too long** (real-world overreach):

```markdown
## Context
Builds the data-layer for PROJ-1234 observability foundation: row count history
for raw tables, run history for pipeline jobs/tests, and a curated registry
mapping scheduler tasks to their destination tables. Five views + one incremental
snapshot + one seed, all materialized to the existing
`<env>_ANALYTICS.OPS_METRICS` schema under a mandatory `obs_*` prefix.

Scout found the upstream framework already populates run results / invocations /
test results (tens of millions of rows fresh daily)...

## Main Changes
- `models/observability/obs_job_runs.sql` view from upstream `RUN_RESULTS` joined to `INVOCATIONS` + `JOBS`
- `models/observability/obs_test_runs.sql` view (resource_type='test' from run_results, joined to `TEST_RESULTS` for failure context)
- `models/observability/obs_invocations.sql` view direct off upstream `INVOCATIONS`
- `models/observability/obs_raw_table_row_count_snapshots.sql` incremental snapshot of `<env>_RAW.INFORMATION_SCHEMA.TABLES`
- `models/observability/obs_scheduler_extract_runs.sql` joining the existing `scheduler.task_instance` source to snapshot deltas
- `seeds/observability/observability_assets.csv` ~50 curated `(dag_id, task_id) -> (db, schema, table)` mappings
- `macros/observability/observability_raw_database.sql` resolves raw DB per target with `--vars` override for dev
- `project.yml`: new `models.observability` + `seeds.observability` groups with `+schema: OPS_METRICS`

## Additional Notes
- Schema reuses the existing `OPS_METRICS` (env-var driven). Analytics role already has RW...
- The snapshot model is `incremental` with composite unique_key...
- For dev runs against the staging raw mirror, pass `--vars '{...}'`...
- `disable_artifact_autoupload: true` stays unchanged...
- Out of scope (separate PROJ-1234 follow-up tickets): dashboard, alerts, anomaly detection...
```

**Right** (same PR, scannable in 10 seconds):

```markdown
## Context
Ticket #: PROJ-1234. Builds the observability surface (row counts + pipeline run history) on top of upstream framework.

## Main Changes
- 5 views + 1 incremental snapshot under `models/observability/`, materialized to `OPS_METRICS`
- `observability_assets` seed: curated `(dag_id, task_id) -> (db, schema, table)` registry
- `observability_raw_database()` macro for dev cross-DB override

## Additional Notes
- Pairs with scheduler PR #200 (hourly trigger DAG); merge data layer first.
- Out of scope: dashboard, alerts, anomaly detection (separate tickets).

## Checklist
- [x] lint + parse/compile green
- [x] seed loaded + tests pass
- [x] schema reuses existing OPS_METRICS (no infra changes)
```

The right version is ~25% the length and reviewers learn the same thing. The eight-line "Main Changes" enumeration became three. The five "Notes" became two - only the ones a reviewer can't infer from the diff.

## Title

PR titles flip to **past tense (v-ed)** - they narrate what the branch did, not what to do. Commit messages stay imperative; only the PR title flips.

- **Length:** ≤ 70 chars
- **Ticket prefix in branch name** (regex `^([A-Z][A-Z0-9]+-[0-9]+)`):
  - Match → `<TICKET>: <v-ed description>` (e.g. `PRJ-123: added OAuth2 login`)
  - No match → `type(scope): <v-ed description>` (conventional-commit shape)
- **Repo/user convention wins.** If the repo validates semantic PR titles, keep
  the type prefix and put the ticket key in brackets after it:
  `chore: [PRJ-123] <description>`.
- **Types** (when no ticket): `feat` | `fix` | `refactor` | `perf` | `docs` | `test` | `chore` | `ci` | `build`
- **Scope:** dominant top-level changed dir

### Ticket branch/title invariant

When work is associated with Jira, Linear, Shortcut, GitHub issue, or another
tracker key:

1. Extract the key from the request, ticket URL, branch, or commits
   (`[A-Z][A-Z0-9]+-[0-9]+` for Jira-style keys).
2. Ensure the PR branch starts with that key before opening/updating the PR.
   Prefer the exact key (`PRJ-123`) unless the user explicitly gave a longer
   convention (`PRJ-123-short-slug`).
3. Use the same key in the PR title. Default: `PRJ-123: <past-tense description>`.
   If semantic PR titles are required: `chore: [PRJ-123] <description>`.

If the branch lacks the key, fix the branch first; do not compensate with only a
ticket-prefixed title.

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
| `PRJ-123-add-oauth` + semantic PR check | `feat: [PRJ-123] added OAuth2 login flow` |
| `feature/oauth-cleanup` | `refactor(auth): consolidated OAuth helpers` |
| `fix/session-leak` | `fix(auth): closed session on logout` |
| `chore/bump-react` | `chore(deps): bumped react to 19.0` |

## Fallback body

Three labelled bullets + a verification block (one field per line). No section headings - eliminates the Summary-vs-Changes overlap by construction. Same shape for 5-line fixes and 500-line features (the **What** bullet nests when needed).

```markdown
- **Why:** <one-sentence motivation>. <Closes #N / Relates to #M if any>
       _OR nested bullets when there are multiple distinct drivers (cap 4)_
- **What:** <semicolon-separated behavior shifts for ≤3 items, OR nested bullets for >3 (cap 7)>
- **Risks:** <breaking changes / migration notes - or `none`>

**Tests:** <✓ what ran / counts - or ✗ N failing, – skipped>
**Docs:** <✓ updated | – N/A>
**Breaking:** <– none | ⚠ see CHANGELOG>
```

> **One field per line** (blank line before the block). GitHub PR bodies render single newlines as breaks, so each field gets its own row - a descriptive `Tests:` value stays readable and never wraps `Docs:`/`Breaking:` onto a stray line. `Tests:` may name what ran (counts + suites); `Docs:`/`Breaking:` stay short. **Don't** collapse the three onto one `·`-joined line - that's the row that wrapped and pushed `Breaking:` onto its own line.

## Per-bullet fill rules

| Bullet | Source | Synthesis rule |
|--------|--------|----------------|
| **Why** | Top of `[Unreleased]` / `[X.Y.Z]` changelog entry → top commit body → branch name verbalized | Default: one sentence; drop low-signal verbs (`add`, `update`), promote the noun, end inline with `Closes #N`. Multiple distinct drivers (compliance + performance + UX) → nest as bullets. Hard cap 4 nested bullets; more means the PR has too many goals. |
| **What** | Commit subjects on the branch, deduped, grouped by behavioral domain | ≤3 items: semicolon-joined on one line. >3: nested bullets. Each item is a *behavior change*, not a file change. Reject "renamed file X" - keep "renamed cookie from `sid` to `__Host-session`". Hard cap 7 nested bullets - more is a scope smell. |
| **Risks** | Breaking-change scan on diff: removed exports, schema migrations, env var changes, removed CLI flags, `BREAKING CHANGE:` in commit body | Lead with severity word: `Breaking - …` / `Migration - …` / `none`. Keep `none` explicit; never omit the bullet. |
| **Verification** | Live `gh pr checks` output for tests; `docs/` files in diff for Docs; same breaking-change scan for Breaking | Three bold-labelled lines, **one field per line** (`**Tests:**` / `**Docs:**` / `**Breaking:**`), preceded by a blank line. `Tests:` may summarize what actually ran (counts + suites, e.g. `✓ 64 backend + frontend schema/Prettier + browser UI check`) since it owns its own row; `Docs:`/`Breaking:` stay short. Never `·`-join all three onto one line (that wraps). Regenerate after CI reports green so reviewers see live status, not a commit-time snapshot. |

## Body examples

**Tiny PR (typo fix):**

```markdown
- **Why:** Fix typo in OAuth provider error message that confused users.
- **What:** corrected `Authentcation failed` → `Authentication failed` in `src/auth/errors.ts`.
- **Risks:** none.

**Tests:** ✓ 127
**Docs:** – N/A
**Breaking:** –
```

**Mid-sized PR (≤3 behavior shifts):**

```markdown
- **Why:** Replace home-rolled session middleware with OAuth2 for security + standards compliance. Closes #42.
- **What:** login redirects to provider OAuth flow; old `/api/login` removed; session cookie renamed to `__Host-session` with Secure+HttpOnly.
- **Risks:** Breaking - existing sessions invalidated on deploy. Documented in CHANGELOG.

**Tests:** ✓ 127
**Docs:** ✓
**Breaking:** ⚠ existing sessions invalidated - see CHANGELOG
```

**PR with multiple motivations (nested Why):**

```markdown
- **Why:**
  - legal flagged session-token storage as non-compliant with new requirements (deadline 2026-06-01)
  - existing middleware leaks request context across goroutines under load (#84)
  - moving to OAuth lets us drop the home-rolled crypto and 600 lines of auth code
- **What:** login redirects to provider OAuth flow; old `/api/login` removed; session cookie renamed to `__Host-session` with Secure+HttpOnly.
- **Risks:** Breaking - existing sessions invalidated on deploy. Documented in CHANGELOG.

**Tests:** ✓ 127
**Docs:** ✓
**Breaking:** ⚠ existing sessions invalidated - see CHANGELOG
```

**Large PR (>3 shifts, nested What):**

```markdown
- **Why:** Replace home-rolled session middleware with OAuth2 (Google + GitHub) for security + standards compliance. Closes #42.
- **What:**
  - login redirects to provider OAuth flow; old `/api/login` removed
  - session cookie renamed `sid` → `__Host-session`; Secure + HttpOnly
  - logout now revokes the provider token, not just the local cookie
  - server fails fast at startup if `OAUTH_GOOGLE_*` / `OAUTH_GITHUB_*` env vars are missing
- **Risks:** Breaking - existing sessions invalidated on deploy. Migration: clients must re-authenticate. Documented in CHANGELOG.

**Tests:** ✓ 412 unit + integration; e2e auth flow green
**Docs:** ✓
**Breaking:** ⚠ see CHANGELOG
```

## Hard rules

- **Repo template, when present, is law** - do not append, do not reorder. Just fill.
- **Issue closers (`Closes #42`)** live inline in the **Why** bullet - no separate Linked-Issues section.
- **Verification block values** come from live tooling output, never the author's claim.
- **Existing PR for this branch** → `gh pr edit`, never re-create.
- **Body transport is invariant:** use `--body-file -` with a quoted heredoc,
  then run the literal-`\n` assertion above.
- **Beta PRs** target dev/beta branch, not main.
- **No AI attribution** in title, body, or PR comments. No "Generated with Claude" / `Co-Authored-By: Claude` / `https://claude.ai/code/session_...` links / emoji unless explicitly asked.
- **`gh pr create --fill`** uses commit messages directly (imperative). After `--fill`, re-edit the title with `gh pr edit --title "<v-ed title>"` to flip it to past tense.
