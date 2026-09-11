---
name: code-review
description: "Review code with a sharp, encouraging voice - inline GitHub PR comments + a tight summary. Supports PR (default), pending changes, commit hash, and codebase modes. Encodes an opinionated review style: severity-prefixed, concise, actionable, no fluff. Pass `--refactor` for the local reuse/slop lens (never posts). For the owned deterministic `miucr` CLI (gated reviews, webhooks, MCP), use vd:miucr."
license: MIT
argument-hint: "[#PR | URL | COMMIT | --pending | codebase | --refactor] [--dry-run] [--post] [--no-inline] [--auto] [--ultra] [--cross-model] [--refactor [--fix] [--save]]"
metadata:
  author: vanducng
  version: "1.2.0"
---

# Code Review

This skill **reviews and reports** - it never implements fixes. If a fix is obvious and one-line, mention it in the comment as a suggestion; hand the actual work back to `vd:cook` / `vd:fix`. Landing the branch afterwards is `vd:ship`.

> **Codex runtime:** this file uses Claude-Code tooling (`AskUserQuestion`, `Task(Explore)` subagents). Under `codex exec` use the self-contained `codex-review.md` in this skill dir instead; per-site fallbacks below also apply.

## Modes

Auto-detect from arguments. Ambiguous or empty → `AskUserQuestion` (Claude Code; plain-text question elsewhere).

| Argument | Mode | Source of diff |
|---|---|---|
| `#123`, `123`, or GitHub PR URL | **PR** *(default & polished path)* | `gh pr diff` |
| 7+ hex chars (`abc1234`) | **Commit** | `git show <sha>` |
| `--pending` | **Pending** | `git diff` (staged + unstaged) |
| `codebase` | **Codebase** | Broad scan via subagents |
| *(none, recent changes in context)* | **Recent** | Whatever was just edited |

Flags:
- `--dry-run` - print the review payload, do NOT post to GitHub (PR mode only)
- `--post` - opposite default; force posting even if other flags would skip
- `--no-inline` - skip inline comments, post only the top-level summary
- `--auto` - non-interactive, default answers, no prompts
- `--ultra` - adversarial review via a dynamic workflow: every finding is independently refuted before it ships (see [Ultra mode](#ultra-mode--adversarial-workflow)). Higher token cost; use for high-stakes diffs.
- `--cross-model` - add reviewers from other model families and weigh findings by agreement (see [Cross-model mode](#cross-model-mode)). Combine with `--ultra` only for release-critical diffs.
- `--refactor` - local reuse / composition / slop lens. Never posts. See [`references/refactor.md`](references/refactor.md). Combine with `--fix` / `--save`. Detect from "refactor review", "is this slop", "does this fit the codebase".

`--refactor` is a two-axis pass when paired with a landing review: run the reuse/slop lens locally first, then the default PR pass. Do not mix the two outputs in one GitHub review.

## Hard rules

1. **One review = one push to GitHub.** Don't dribble out comments across multiple `gh` calls. Build the full payload, then submit a single `POST /pulls/:n/reviews`. The author gets one notification, not 12.
2. **Inline beats top-level.** If a finding maps to a specific file:line, it MUST go inline. Top-level summary is for context, verdict, and orphan concerns that don't anchor to a hunk.
3. **No critical claim without evidence.** "Critical" means "merge would cause incident / data loss / security hole." If you can't point to the failure mode, downgrade to Important.
4. **Encouraging tone, firm content.** Lead with what works when it's true. Be direct about problems. Never sarcastic. Never "as an AI…". The author is a peer.
5. **Read the file, not just the hunk.** Diff context lies. Open the file at the changed lines and 30 lines around to understand surrounding state before commenting.
6. **Intent vs mistake.** Review whether the change achieves the stated intent, not whether the intent is right. A finding that challenges a deliberate product decision, a named tradeoff, or two valid designs is `**Question:**`, never Critical/Important, and must not flip the verdict to Request changes. Relay it; let the author/user answer.
7. **Stay in the diff.** Comment on paths this change touches. Adjacent cleanup is out of scope unless this diff introduces a merge-blocking defect there.

## Review voice (the style guide)

These are the conventions for **every** comment this skill writes. Reference example: `<org>/<repo>#124`.

### Severity prefix on every finding

| Prefix | When | Notification cost |
|---|---|---|
| `**Critical:**` | Blocks merge. Bug, security, data loss, CI red. | High - author must act before next push. |
| `**Important - <topic>**:` | Should fix before merge. Correctness, design, perf. The `<topic>` makes the comment skimmable. | Medium. |
| `**Suggestion:**` | Nice-to-have. Style, minor refactor, doc nit. | Low - author can ignore. |
| `**Question:**` | You genuinely don't know, or the finding challenges a product/intent choice the author may have made on purpose. Asks; never blocks merge by itself. | Low - invites dialog, not blocking. |
| `**Nit:**` | Pure preference. Optional. | Zero - must be ignorable. |

### Comment shape

```
**<Severity prefix>**: <one-sentence problem statement>.

<1-3 sentences of evidence: what breaks, when, why it matters. Include the
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

Tone: encouraging when earned (don't fake-praise), direct on real problems (no "maybe consider perhaps"), curious on unknowns, never condescending ("obviously" / "clearly" / "I'm surprised this passed").

## PR mode - the polished path

### 1. Fetch context

```bash
PR=$1   # accepts "#123", "123", or full URL - normalize to number
gh pr view  "$PR" --json title,body,author,baseRefName,headRefName,files,additions,deletions,state,reviewDecision,headRefOid
gh pr diff  "$PR"
# Exit 8 = pending (retry), not "no checks". Print the table; ignore the rc.
gh pr checks "$PR" || true
```

Capture `headRefOid` - every inline comment's `commit_id` MUST equal this so comments stay anchored if the author force-pushes mid-review.

### 2. Decide the scope of effort

| Diff size | Approach |
|---|---|
| < 300 lines | Read every changed file in full (file, not hunk). Manual pass. |
| 300-1500 lines | Read full files for security-sensitive or core-logic changes; spot-check the rest. |
| > 1500 lines | Batch via parallel `Task(Explore)` subagents grouped by directory; synthesize findings. Don't pour the whole diff into your context. No subagents (Codex) → review directory-by-directory sequentially, or use `codex-review.md`. |

### 3. Build the review payload

Collect findings as you go into this structure (memory only - don't write a file):

```json
{
  "commit_id": "<headRefOid>",
  "event":     "APPROVE | REQUEST_CHANGES | COMMENT",
  "body":      "<top-level summary, per the shape above>",
  "comments": [ { "path": "<file>", "line": 44, "side": "RIGHT", "body": "**Important - <topic>**: ..." } ]
}
```

**`line` rules:**
- `line` is the line number in the file at `commit_id` (the new version for additions, the old version with `"side": "LEFT"` for deletions).
- For a multi-line comment, use `start_line` + `line`. Both on the same `side`.
- If the targeted line is unchanged context (not in the diff), GitHub rejects the comment. In that case, anchor to the nearest changed line and reference the real line in the body: *"Re. L44 (unchanged): …"*.

### 4. Post the review

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

### 5. Confirm

After posting, print the event, the inline-comment count, and the review `html_url` from the API response.

## Ultra mode - adversarial workflow

`--ultra` swaps the single-context review pass for a **dynamic Workflow** (Claude Code's `Workflow` tool) that structurally removes self-preferential bias: the agent that *finds* an issue is never the one that *confirms* it. Reach for it when a wrong call is expensive (security-sensitive change, large refactor, release diff) - not for a routine 50-line PR.

**How it runs.** The template is `workflows/adversarial-review.js` - read it, adapt `DIMENSIONS` / `votes` to the diff, then invoke the `Workflow` tool with `args`:

```jsonc
{ "pr": 123, "votes": 3 }        // or { "diffCmd": "git diff", "votes": 3 }
```

It composes two patterns:

1. **Review (fan-out)** - one agent per dimension (`correctness`, `security`, `reliability`, `performance`, `api`, `tests`), each with clean context, mapping onto the [Checklist](#checklist-apply-to-every-diff) so coverage doesn't degrade the way a single long pass does.
2. **Verify (adversarial)** - each candidate finding faces `votes` independent refuters prompted to *kill* it; majority-refute drops it. Only survivors come back.

**Then post as normal.** The workflow returns `{ confirmed, dropped }`. Map `confirmed` into the same review payload (§3) and post the **one** review (§4) with the usual severity prefixes and voice. Mention the filter in the summary: *"Adversarial pass: N findings confirmed, M refuted and dropped."* `--dry-run` still prints instead of posting.

**Portability & cost.** The `Workflow` tool is Claude Code-only - in another runtime, fall back to the standard pass and say so. Ultra spends materially more tokens (≈ dimensions × findings × votes agents); the default non-ultra path remains correct for everyday reviews.

## Cross-model mode

`--ultra` removes self-preferential bias; `--cross-model` removes *family* bias - models share blind spots with their own outputs and priors, so a second family catches what the first cannot. Adapted from cursor/plugins pstack interrogate (MIT).

**How it runs.**

1. State the change's intent in one paragraph (from the PR body, commits, or the user). Reviewers challenge whether the work achieves the intent, not whether the intent is right.
2. Run the standard pass here, then send the *same* diff + intent + the [Checklist](#checklist-apply-to-every-diff) to one or two reviewers on different model families - `codex exec` / `gemini` / `opencode run`, whichever is on PATH. No personas: the adversarial signal comes from model diversity. A family that is unavailable is reported as skipped, never simulated.
3. Synthesize with lead judgment - you are a pragmatic senior engineer with the full context, not a neutral aggregator. Dedupe, then bucket every finding: **act on** (correctness/security given the actual goals), **consider** (legitimate, cost unclear), **noted** (valid, not actionable now), **dismissed** (wrong or missing context - say why). Tag each with the families that raised it: 2+ families = high signal; a lone-family finding is read and weighed, never auto-promoted.
4. Post the **one** review as normal (§4). Summary names the panel: *"Cross-model pass: A+B agreed on N, lone-family M, dismissed K."*

**Cost.** One extra full-diff pass per family. Use for security-sensitive, migration, or release diffs - not routine PRs.

## Non-PR modes (quick reference)

- **`--pending`** - `git diff` + `git diff --cached`; same severity/voice rubric, stdout report (the author runs it pre-push).
- **Commit hash** - `git show <sha>`; same review, no post target (reviewing someone else's commit after the fact).
- **`codebase`** - not the polished PR path: spawn `Task(Explore)` subagents per top-level dir (no subagents → scan each dir inline, sequentially), each returning findings as file:line:severity:body; synthesize into one report at the injected `Reports:` path as `code-review-<date>-<slug>.md`.

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
- Calibrate: if the code is correct, safe, and readable, ship it - don't manufacture findings to look thorough. "Different from how I'd write it" is not a finding (intent-vs-mistake is Hard rule 6).

## CI handling

When `gh pr checks` shows failures:

1. Identify the failing job and its run ID; the summary's first finding is `**Critical:** CI <job> is red ([run-id](url)).`
2. Include `gh run view <run-id> --log-failed` so the author can inspect; if the cause is obvious from the diff (lint, type error, missing import), name it - don't make the author hunt.
3. Verdict is at least `Request changes` while CI is red. No exceptions.

## When the answer is "approve"

A real verdict, not a participation trophy. `Approve` = no Critical, no Important finding, tests cover the change, CI green (or only tolerated flakes). Body: `Approved. <one sentence on what shipped well>` plus at most 1-2 inline suggestions.

## Workflow position

`vd:cook` → `vd:code-review` → `vd:ship` (or `vd:fix` if changes requested). Also fires standalone on a teammate's PR or the local branch before `vd:ship`.
