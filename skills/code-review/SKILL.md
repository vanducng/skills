---
name: code-review
description: "Review code with a sharp, encouraging voice - inline GitHub PR comments + a tight summary. Reviews on two axes (Spec fidelity + Standards) via parallel subagents. Supports PR (default), pending changes, commit hash, codebase, and --refactor ('does this fit the codebase / is this slop' - local, report-only) modes. Encodes an opinionated review style: severity-prefixed, concise, actionable, no fluff."
license: MIT
argument-hint: "[#PR | URL | COMMIT | --pending | codebase | --refactor] [--dry-run] [--post] [--no-inline]"
metadata:
  author: vanducng
  version: "1.2.0"
---

# Code Review

## What this skill is - and isn't

| Skill | Question it answers | Output |
|---|---|---|
| `vd:scout` | "Where does this code live?" | Pointers |
| `vd:debug` | "Why is this broken?" | Root cause |
| **`vd:code-review`** | **"Is this change ready to land, and what should the author fix?"** | **Inline PR comments + summary verdict** |
| `vd:ship` | "Land the branch." | Merged + tagged + PR |

This skill **reviews and reports**. It does not implement fixes. If a fix is obvious and one-line, mention it in the comment as a suggestion - but don't apply it. Hand back to `vd:cook` / `vd:fix` for the actual work.

> **Codex runtime:** this file uses Claude-Code tooling (`AskUserQuestion`, `Task(Explore)` subagents). Under `codex exec` use the self-contained `codex-review.md` in this skill dir instead; per-site fallbacks below also apply.

## Modes

Auto-detect from arguments. Ambiguous or empty → `AskUserQuestion` (Claude Code; plain-text question elsewhere).

| Argument | Mode | Source of diff |
|---|---|---|
| `#123`, `123`, or GitHub PR URL | **PR** *(default & polished path)* | `gh pr diff` |
| 7+ hex chars (`abc1234`) | **Commit** | `git show <sha>` |
| `--pending` | **Pending** | `git diff` (staged + unstaged) |
| `codebase` | **Codebase** | Broad scan via subagents |
| `--refactor` | **Refactor** - "does this fit the codebase, or is it slop?" Local, report-only, never posts. Full lens: [`references/refactor-lens.md`](references/refactor-lens.md) | `git diff` / ref range / `gh pr diff` |
| *(none, recent changes in context)* | **Recent** | Whatever was just edited |

Flags:
- `--dry-run` - print the review payload, do NOT post to GitHub (PR mode only)
- `--post` - opposite default; force posting even if other flags would skip
- `--no-inline` - skip inline comments, post only the top-level summary
- `--auto` - non-interactive, default answers, no prompts
- `--ultra` - adversarial review via a dynamic workflow: every finding is independently refuted before it ships (see [Ultra mode](#ultra-mode--adversarial-workflow)). Higher token cost; use for high-stakes diffs.

## Hard rules

1. **One review = one push to GitHub.** Don't dribble out comments across multiple `gh` calls. Build the full payload, then submit a single `POST /pulls/:n/reviews`. The author gets one notification, not 12.
2. **Inline beats top-level.** If a finding maps to a specific file:line, it MUST go inline. Top-level summary is for context, verdict, and orphan concerns that don't anchor to a hunk.
3. **No critical claim without evidence.** "Critical" means "merge would cause incident / data loss / security hole." If you can't point to the failure mode, downgrade to Important.
4. **Encouraging tone, firm content.** Lead with what works when it's true. Be direct about problems. Never sarcastic. Never "as an AI…". The author is a peer.
5. **Read the file, not just the hunk.** Diff context lies. Open the file at the changed lines and 30 lines around to understand surrounding state before commenting.

## Review voice (the style guide)

These are the conventions for **every** comment this skill writes. Reference example: `careernowbrands/cnb-data-contract#124`.

### Severity prefix on every finding

| Prefix | When | Notification cost |
|---|---|---|
| `**Critical:**` | Blocks merge. Bug, security, data loss, CI red. | High - author must act before next push. |
| `**Important - <topic>**:` | Should fix before merge. Correctness, design, perf. The `<topic>` makes the comment skimmable. | Medium. |
| `**Suggestion:**` | Nice-to-have. Style, minor refactor, doc nit. | Low - author can ignore. |
| `**Question:**` | You genuinely don't know if it's a bug. Asks the author. | Low - invites dialog, not blocking. |
| `**Nit:**` | Pure preference. Optional. | Zero - must be ignorable. |

### Comment shape

```
**<Severity prefix>**: <one-sentence problem statement>.

<1–3 sentences of evidence: what breaks, when, why it matters. Include the
actual symptom - not just "may cause issues">.

<Optional: suggested change, in fenced block or inline code>.

<Optional: question to author if the fix path is unclear>.
```

**Do:**
- Open with the problem, not the praise. (Praise goes in the summary.)
- Quote the offending fragment in fenced code when correcting a specific value.
- Name the failure mode explicitly: *"alert silently won't fire"*, *"PII leaks to logs on retry"*, *"locks the table for the duration of the migration"*.
- Suggest a concrete alternative when you have one: `CURRENT_DATE - 1` not "use the right date".
- Cross-link related comments when the issues compound: *"combined with the threshold on L81…"*.

**Don't:**
- Don't pad with hedges. "It might possibly be a small concern that perhaps…" → "This will fail when X."
- Don't restate the diff. The author already wrote the code.
- Don't moralize ("you should always…"). State the consequence: "this breaks X."
- Don't use emojis or icons (severity badges/PNGs) unless the repo's review conventions already use them. Plain `**Severity:**` ships everywhere.
- Don't comment on every line. If a file has 5 issues, the worst 2 are usually enough. The author will find the rest when they fix those.

### Top-level summary shape

Keep under 8 lines. Structure:

```
<One sentence on what the PR does + what works>.

<If CI is failing: Critical: CI <job> is red (link/run-id). Block merge until fixed:
exact command to debug>.

<One line pointing at inline comments>: "Inline comments cover the
<correctness / design / perf> concerns."

<Verdict - see below>.
```

**Verdict line** - exactly one of:
- `Approve` - no Critical, no Important. Suggestions OK.
- `Request changes` - at least one Critical or Important. List the topics.
- `Comment` - Only Suggestions / Questions / Nits. Author decides.

### Tone calibration

- **Encouraging when it's earned.** "Solid coverage on the happy path" / "Nice catch on the parameterized query - easy to get wrong." Don't fake-praise.
- **Direct on real problems.** "This deadlocks under concurrent writes." Don't soften with "maybe consider perhaps."
- **Curious on unknowns.** "What's the intended behavior when X is null? The current branch silently drops it."
- **Never condescending.** Never "obviously" / "clearly" / "any junior dev would know" / "I'm surprised this passed".

## PR mode - the polished path

This is the path that produces the GitHub artifact. Treat it as the primary mode.

### 1. Fetch context

```bash
PR=$1   # accepts "#123", "123", or full URL - normalize to number
gh pr view  "$PR" --json title,body,author,baseRefName,headRefName,files,additions,deletions,state,reviewDecision,headRefOid
gh pr diff  "$PR"
gh pr checks "$PR" 2>/dev/null || echo "(no checks)"
```

Capture `headRefOid` - every inline comment's `commit_id` MUST equal this so comments stay anchored if the author force-pushes mid-review.

### 2. Decide the scope of effort

| Diff size | Approach |
|---|---|
| < 300 lines | Read every changed file in full (file, not hunk). Manual pass. |
| 300–1500 lines | Read full files for security-sensitive or core-logic changes; spot-check the rest. |
| > 1500 lines | Batch via parallel `Task(Explore)` subagents grouped by directory; synthesize findings. Don't pour the whole diff into your context. No subagents (Codex) → review directory-by-directory sequentially, or use `codex-review.md`. |

### 3. Review on two axes

Pin the diff to a fixed ref first (`headRefOid` for PRs, `HEAD` otherwise) - the review target must not move mid-pass. Then review along two independent axes:

- **Spec fidelity** - does the change do what was agreed, all of it, and nothing beyond it? Find the spec in order: PR body → linked issue → plan dir (`plan.md` + phase files) → the conversation. Flag missing scope, silent extra scope, and behavior that contradicts a stated decision.
- **Standards** - is the code well built regardless of what it was supposed to do? Correctness/security/reliability per the [Checklist](#checklist-apply-to-every-diff), plus the smells baseline in [`references/code-smells.md`](references/code-smells.md).

Run the axes as **two parallel subagents** (`Task(Explore)` / `general-purpose`), each getting the diff + only its axis brief - isolation is the point: the spec reader shouldn't be primed by style complaints and vice versa. Cap each subagent's report at ~400 words. Aggregate **without reranking** - merge both finding lists into the payload, keep each axis's severities as given, and note in the summary which axis each Critical came from. No subagent tool → run the two passes sequentially yourself, spec axis first, in separate fresh looks.

Skip the fan-out for trivial diffs (<50 lines, no spec to check) - a single pass with both hats on is proportionate there.

### 4. Build the review payload

Collect findings as you go into this structure (memory only - don't write a file):

```json
{
  "commit_id": "<headRefOid>",
  "event":     "APPROVE | REQUEST_CHANGES | COMMENT",
  "body":      "<top-level summary, per the shape above>",
  "comments": [
    {
      "path":      "contracts/constraints/snowflake/five9_old_lead_recency_alert.yaml",
      "line":      44,
      "side":      "RIGHT",
      "body":      "**Important - CURRENT_DATE timing**: ..."
    }
  ]
}
```

**`line` rules:**
- `line` is the line number in the file at `commit_id` (the new version for additions, the old version with `"side": "LEFT"` for deletions).
- For a multi-line comment, use `start_line` + `line`. Both on the same `side`.
- If the targeted line is unchanged context (not in the diff), GitHub rejects the comment. In that case, anchor to the nearest changed line and reference the real line in the body: *"Re. L44 (unchanged): …"*.

### 5. Post the review

Default behavior:
- PR mode + no `--dry-run` → **post** via single `gh api` call (see below).
- PR mode + `--dry-run` → **print** the JSON payload, exit, do not call the API.
- Non-PR modes → **print** the findings as a markdown report. Never post.
- GitHub rejects `APPROVE` reviews from the PR author. If the authenticated user is the author and the verdict is `Approve`, submit the same body as `COMMENT` and say a different reviewer is required for branch-protection approval.

```bash
gh api \
  -X POST \
  "repos/$OWNER/$REPO/pulls/$PR_NUM/reviews" \
  --input - <<< "$PAYLOAD_JSON"
```

If the call returns 422 with `Pull request review thread line must be part of the diff`, the comment anchored to an unchanged line. Move it to the nearest diff line and retry - once. Never auto-retry more than once; surface the error to the user.

### 6. Confirm

After posting, print:
```
Posted review to PR #<n> as <event>:
  • <count> inline comments
  • Verdict: <event>
  • URL: <html_url from API response>
```

## Ultra mode - adversarial workflow

`--ultra` swaps the single-context review pass for a **dynamic Workflow** (Claude Code's `Workflow` tool) that structurally removes self-preferential bias: the agent that *finds* an issue is never the one that *confirms* it. Reach for it when a wrong call is expensive (security-sensitive change, large refactor, release diff) - not for a routine 50-line PR.

**How it runs.** The template is `workflows/adversarial-review.js` - read it, adapt `DIMENSIONS` / `votes` to the diff, then invoke the `Workflow` tool with `args`:

```jsonc
{ "pr": 123, "votes": 3 }        // or { "diffCmd": "git diff", "votes": 3 }
```

It composes two patterns:

1. **Review (fan-out)** - one agent per dimension (`correctness`, `security`, `reliability`, `performance`, `api`, `tests`), each with its own clean context. They map onto the [Checklist](#checklist-apply-to-every-diff) below, so coverage doesn't degrade the way a single long pass does (no "addressed 20 of 50" laziness).
2. **Verify (adversarial)** - each candidate finding faces `votes` independent refuters prompted to *kill* it. Majority-refute drops the finding. Only survivors come back.

**Then post as normal.** The workflow returns `{ confirmed, dropped }`. Map `confirmed` into the same review payload (§4) and post the **one** review (§5) with the usual severity prefixes and voice. Mention the filter in the summary: *"Adversarial pass: N findings confirmed, M refuted and dropped."* `--dry-run` still prints instead of posting.

**Portability & cost.** The `Workflow` tool is Claude Code-only - in another runtime, fall back to the standard pass and say so. Ultra spends materially more tokens (≈ dimensions × findings × votes agents); the default non-ultra path remains correct for everyday reviews.

## Non-PR modes (quick reference)

### `--pending` (local, pre-commit)

`git diff` + `git diff --cached`. Apply the same severity/voice rubric. Output to stdout as a markdown report. The author runs this themselves before pushing.

### Commit hash

`git show <sha>`. Same review, no post target. Useful for reviewing someone else's commit after the fact.

### `codebase` / `codebase parallel`

Out of scope for the polished PR path. Spawn `Task(Explore)` subagents per top-level dir (no subagents → scan each dir inline, sequentially); each returns a findings list with file:line:severity:body. Synthesize into a single markdown report. Write to the injected `Reports:` path. Filename: `code-review-<date>-<slug>.md`.

## Checklist (apply to every diff)

This is the always-on lens. Repo-specific rules (i18n, SQL store conventions, mobile UI…) live in the project's `CLAUDE.md` or `docs/code-standards.md` - read those first and layer them on top of this list.

**Correctness**
- Off-by-one, nil/null deref, missing error handling, swallowed errors.
- Race conditions, goroutine leaks, channel ownership, unprotected shared state.
- Edge cases on inputs the author probably didn't test (empty, zero, max, unicode, timezone, DST).

**Security**
- Injection - SQL, command, template, XSS. Look for string concat or `fmt.Sprintf` into queries/shells/HTML.
- Hardcoded secrets, tokens, API keys. Anything resembling base64 or hex of ≥32 chars.
- Auth scoping. `userID` vs `tenantID` vs `sessionID` - never trust the wrong one.
- SSRF, path traversal, open redirect on any URL/path read from input.

**Reliability**
- Retries without idempotency keys.
- Unbounded queues, channels, slices, caches.
- Timeouts: any network call without an explicit timeout is a finding.
- Migrations: any schema change must be reversible OR the PR must call out the irreversibility.

**Performance** (only if there's evidence, not vibes)
- N+1 queries - loop over IDs each issuing a DB call.
- Full table scans on hot paths - verify WHERE/JOIN/ORDER BY against existing indexes (check migrations).
- Allocations in hot loops (Go: profile-guided only; don't pre-optimize).
- Framework AI-slop: `useEffect` for data already in render scope, missing `key`/`useMemo` on heavy lists, `SELECT *` then filter in app code, await-in-loop where a batch call exists. Real, common, cheap to flag.

**Dependencies**
- New dependency for something the stdlib or an existing dep already does → ask "why not the one we have?"
- A heavy/transitive-heavy package for a few lines of logic → flag (supply-chain surface + bundle/binary weight).
- Version bumps that cross a major, or lockfile churn unrelated to the PR's purpose → call out.
- Unpinned/`latest` or a brand-new low-adoption package on a critical path → security finding, not a nit.

**API surface & breakage**
- Renamed/removed exports → downstream breaks.
- Changed response shape / status codes → client breaks.
- Config-file schema change → ops breaks. Needs a migration note or backwards-compat shim.

**Testing**
- New code paths covered? Edge cases tested, not just happy path?
- Tests touching real DB or mocks - match the repo's existing convention. Don't mix.
- Are there tests that would catch the bug if the author re-introduced it tomorrow? If no, ask for one.

**Change shape**
- Refactor + new behavior in one PR → ask to split. A reviewer can't tell a behavior change from a move when they're tangled, and a bad refactor hides inside the feature diff.
- Dead/zombie code: a function/flag/branch the diff stops calling but leaves behind → flag and *ask* (it may be load-bearing elsewhere - don't assert "remove it"). Same for commented-out blocks.

**Project conventions**
- Read `CLAUDE.md`, `docs/code-standards.md`, `docs/system-architecture.md` if present. Apply repo-specific rules (i18n keys in 3 locales, h-dvh not h-screen, parameterized SQL, etc.).
- Calibrate: this is a review, not a rewrite. If the code is correct, safe, and readable, ship it - don't manufacture findings to look thorough. "Different from how I'd write it" is not a finding.

## CI handling

When `gh pr checks` shows failures:

1. Identify the failing job and its run ID.
2. The summary's first finding is `**Critical:** CI <job> is red ([run-id](url)).`
3. Include the exact command for the author to inspect: `gh run view <run-id> --log-failed`.
4. If the failure cause is obvious from the diff (e.g. lint, type error, missing import), name it in the comment body. Don't make the author hunt.
5. Verdict is at least `Request changes` while CI is red. No exceptions.

## When the answer is "approve"

It's a real verdict, not a participation trophy. Use it when:
- No Critical, no Important findings.
- Suggestions/Nits are fine to include.
- Tests cover the change.
- CI is green (or only flakes the repo is known to tolerate).

Approval body - keep it short:
```
Approved. <one sentence on what shipped well>.

<Optional: 1–2 suggestion comments inline>.
```

## Anti-patterns (don't do these)

- **Comment dump.** 40 comments on a 200-line diff. Pick the worst 5–10.
- **"LGTM 🚀".** Empty approvals teach nothing and erode trust in your reviews. Either approve with a specific reason, or don't approve.
- **Ghost suggestions.** "Consider refactoring this." → useless. Either propose the refactor with code, or drop the comment.
- **Re-reviewing on every push.** If the author pushed a 3-line fix to address your Critical, look at those 3 lines - don't re-review the whole PR.
- **Hidden assumptions.** "This should use the foo pattern." → name the file, name the pattern, link the prior art.

### Common rationalizations to catch (in the code, and in yourself)

| The author says (or the diff implies) | The reviewer's job |
|---|---|
| "It works, ship it" | Working ≠ correct. Check the edge cases the happy path skipped. |
| "I'll add tests in a follow-up" | The follow-up rarely comes. Untested new logic is a finding now. |
| "It's just a small change" | Small diffs hide auth/data/migration blast radius. Size ≠ risk. |
| "TODO / fix later" added in this PR | Either it matters (do it) or it doesn't (delete it). A new TODO on a critical path is a finding. |
| "Temporary workaround" | Temporary code is permanent code. Demand the real fix or a tracked issue link. |

## Workflow position

```
vd:cook  →  vd:code-review (this skill)  →  vd:ship
                                             (or vd:fix if changes requested)
```

Also fires standalone when the user invokes on a teammate's PR or to review the local branch before `vd:ship`.
