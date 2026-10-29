---
name: miucr
description: Set up and run the `miucr` AI code-review CLI (miu-cr). Use when asked to set up miucr in a repo, review staged changes, a commit, a branch range, or a GitHub PR, gate a review in CI, check provider login or config, inspect past reviews, or keep a PR review loop going until it is merge-ready. Output is the `miucr.cli/v1` JSON envelope; parse it, don't grep prose.
---

# miucr

`miucr` reviews diffs. The engine selects files, assembles context, re-anchors
findings to real lines, gates, and dedupes; the model only finds bugs and
proposes fixes. Every command prints one JSON envelope on stdout.

For anything not covered here, ask the source of truth instead of guessing:

- `miucr <command> --help` for exact flags and defaults.
- `https://cr.miu.sh/<page>.md` for raw docs: `onboarding`, `usage`, `github-pr`,
  `serve-and-action`, `rules`, `providers`, `credentials`, `mcp`, `history`,
  `evaluation`, `store-backends`, `architecture`. Index: `https://cr.miu.sh/llms.txt`.

## Set up a repo

Run in order and stop at the first step that needs the user.

1. `miucr version` - if missing, install: `curl -fsSL https://cr.miu.sh/install.sh | sh`.
   `miucr upgrade --check` reports a newer release; upgrade only if the user agrees.
2. Auth. `miucr config show` shows the default provider. Pass if one holds:
   - `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is set, or a provider has an `auth_command`.
   - `miucr whoami` shows a valid OAuth login.
   Otherwise ask the user to pick: `miucr login --provider openai` (ChatGPT plan, opens
   a browser) or export an API key. Never ask them to paste a key into chat.
3. Config, only if none exists: `miucr init --non-interactive --provider <anthropic|openai> --auth <env|oauth> --yes`.
4. Rules: if `.miu/cr/rules/` is empty, `miucr rules init`, then edit the scaffold for
   this stack (frontmatter `globs`, prose is reviewer context). Verify with
   `miucr rules check <a changed file>`.
5. First review: `miucr review --staged -o json` (or `--from main --to HEAD` if nothing is staged).

## Commands

| Goal | Command |
|---|---|
| Staged changes | `miucr review --staged` |
| Branch vs main (merge-base) | `miucr review --from main --to HEAD` |
| One commit | `miucr review --commit <sha>` |
| Fail on severity (exit 2) | add `--gate high` (`none\|info\|low\|medium\|high\|critical`) |
| Large or cross-file change | add `--deep-context` |
| Steer this run | add `--instruction "focus on auth"` |
| PR dry-run | `miucr review --pr owner/repo#N` |
| PR publish | `miucr review --pr owner/repo#N --post` (needs `GITHUB_TOKEN`) |
| Re-review an unchanged head | add `--force` |
| Past reviews | `miucr history`, `miucr history show <id>` |
| What the model saw | `miucr trace <id>` or `miucr trace owner/repo#N` |
| Effective config | `miucr config show` |

`-o pretty` is for humans; keep the default JSON when you parse.
Write actions on `--pr --post` are opt-in: `--suggest` (one-click suggestions),
`--approval clean|threshold`. Only add them when the user asks.

## Output contract

```json
{ "ok": true, "api_version": "miucr.cli/v1", "kind": "review.result", "command": "review",
  "summary": { "findings": 2, "gate": "high" },
  "data": { "findings": [ { "file": "...", "line": 42, "end_line": 42, "title": "...",
            "severity": "high", "category": "correctness", "rationale": "...",
            "suggested_patch": "...", "quoted_code": "..." } ],
            "stats": { "files_reviewed": 3, "findings_total": 2, "findings_dropped": 0 },
            "review_id": "rev_..." },
  "artifacts": [], "warnings": [] }
```

- Branch on `ok`. On `ok:false`, read `error.code`, `error.hint`, `error.retryable`.
- Exit `0` clean, `1` operational error, `2` gate tripped or bad invocation, `130` canceled.
  On a gate trip the findings envelope still prints before the error.
- `--pr` adds `data.pr` (head SHA, posted counts, `approve_action`). An unchanged head returns `data.skipped_unchanged: true` with no model call.

| `error.code` | Do |
|---|---|
| `agent.auth_failed`, `agent.auth_expired` | Fix the key or rerun `miucr login`. Do not retry. |
| `provider.rate_limited`, `agent.unavailable` | Retry later; check `error.details.resets_in_seconds`. |
| `review.timeout` | Raise `--timeout 1800s` or narrow the diff (`--include`, `--exclude`). |
| `config.invalid` | Fix the named config field or flag value. |
| `quota.exceeded` | Wait for the window or raise `[providers.<name>.quota]`. |
| `github.auth`, `github.pr_not_found` | Check `GITHUB_TOKEN` scope and the PR ref. |
| `github.rate_limited`, `github.unavailable`, `store.unavailable` | Retry. |
| `internal.error` | Report it with the `request_id`. |

## Local fix loop

1. `miucr review --staged --gate high -o json`.
2. For each finding at or above the user's bar, open `file:line`, confirm against
   the source, and fix it. Treat a finding as a claim to verify, not an order.
3. Re-stage and rerun until clean or the remaining findings are rejected with a reason.

## PR review loop

Use when asked to keep a PR reviewed until merge-ready. One controller per PR:
do not run this beside `miucr serve --poll` on the same PR.

1. Preflight: `gh pr view <n> --json state,isDraft,headRefOid,mergeStateStatus,statusCheckRollup`.
   Stop on merged, closed, draft, or conflict, and report why.
2. One review per new head SHA:
   `miucr review --pr owner/repo#N --post --deep-context --conversation -o json`.
   Record `data.review_id` and `data.pr.head_sha`. Re-fetch `headRefOid` after; if it
   moved, start over on the new head.
3. For each open finding thread: verify it, fix it or decide not to, push, then reply
   on that thread in one of these forms (miucr judges the reply and resolves the
   thread when it holds):
   - `Fixed in <sha>: <what changed>`
   - `Deferred: <reason and where it is tracked>`
   - `Not applicable: <why>`
4. Repeat on each new head until checks are green and no open findings remain.
   Report merge-ready. Merge only if the user explicitly said to.

## CI and hosting

- GitHub Action: copy `examples/github-action/code-review.yml` into
  `.github/workflows/` and add the provider key as a repo secret.
- Self-hosted: `miucr serve` (webhook, `--poll`, REST). See `serve-and-action.md`.
- MCP: `miucr mcp` exposes `review_run` and `review_get` over stdio. See `mcp.md`.

## Privacy

Keys come from env, flags, or `miucr login` at runtime and are never persisted
by miucr. Never write a key, token, or real reviewed code into files, commits,
or examples.
