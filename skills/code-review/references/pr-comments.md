# Posting the review on GitHub

The verdict file is the record, and `**Critical:**` is an Important finding whose failure mode is an incident; this is how to also post it on the PR when the seat's role or the user asks for it (`--post`). One review per push, findings inline, the severity prefix mapped from the verdict tags: Important -> `**Important - <topic>**:`, Nit -> `**Nit:**`, Pre-existing -> `**Suggestion:**` naming it pre-existing. Keep the finding ids (F1, F2) in each comment so the outcome counts join.

## Targets without a slice

| Target | `--base` / `--head` for `verdict.cjs` | Spec axis |
|---|---|---|
| A PR | `--base origin/<baseRefName>` (from `gh pr view --json baseRefName`) | `inconclusive` unless the PR names its spec |
| A commit | `--base <sha>^ --head <sha>` | as above |
| Uncommitted changes | none: nothing is committed to bind, so report findings without a verdict file | n/a |
| A whole codebase | not a diff review: use `vd:security` or `--refactor` | n/a |

The old `--dry-run` is the default now (nothing posts without `--post`); `--auto` is gone because there are no prompts; `--ultra` and `--cross-model` are gone because they spawn agents, and a second family's verdict is a second reviewer seat, not this one.

## Review voice (the style guide)

These are the conventions for **every** comment this skill writes. 

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
| > 1500 lines | Review directory by directory, in sequence, keeping notes per directory; never spawn agents for it. Ask for a split when the change mixes concerns. |

### 2b. Prove it against the live system

Tests and CI prove the code runs, not that it does the right thing on real data. When the diff changes a query, a selection or ranking rule, a data contract, or what a downstream reader (model prompt, report, alert) receives, run the changed logic read-only against real data before writing findings: grain, coverage, hardcoded values vs upstream, grants, freshness, and whether the consumer actually sees the evidence a label is based on. Probes and safety rules: [`references/live-verification.md`](references/live-verification.md).

Skip it for pure refactors, copy changes, and diffs with no data or runtime surface.

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


## CI handling

When `gh pr checks` shows failures:

1. Identify the failing job and its run ID; the summary's first finding is `**Critical:** CI <job> is red ([run-id](url)).`
2. Include `gh run view <run-id> --log-failed` so the author can inspect; if the cause is obvious from the diff (lint, type error, missing import), name it - don't make the author hunt.
3. Verdict is at least `Request changes` while CI is red. No exceptions.

## Re-review after the author pushes

1. Diff the head you reviewed against the new head. A reply saying "fixed" is not the fix.
2. Check each finding at the new head. Unless `--dry-run`: fixed → resolve your own thread; not fixed → reply on it and keep it open. Thread state can't ride in the review POST, so this is the one exception to Hard rule 1.
3. When the change has a runtime path, offer one end-to-end run and reconcile its output with the source of truth ([`references/live-verification.md`](references/live-verification.md#end-to-end-run)). It runs read-only by default; any write or post in it needs the user's go-ahead and never happens under `--auto`.
4. Read every unresolved thread at the current head, bot reviewers included. Decide blocking or not; name the non-blocking ones in the review body.
5. Refresh `headRefOid` and checks right before submitting, then submit the review against that SHA with the verdict the rules above give (author-can't-approve fallback included).

