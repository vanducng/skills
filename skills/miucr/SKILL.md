---
name: miucr
description: Review code/diffs/PRs with the owned `miucr` CLI (miu-cr, a pure-Go AI code reviewer). Use when asked to review staged changes, a commit, a ref range, or a GitHub PR; to run/parse a gated review; compare reviewer quality with eval; to drive reviews over MCP; or to run the serve webhook/poll daemon or GitHub Action. Output is the stable `miucr.cli/v1` JSON envelope; parse it, don't grep prose.
---

# miucr: owned AI code-review CLI (v0.65.0)

`miucr` (the **miu-cr** project) is a fast, **pure-Go** (`CGO_ENABLED=0`) AI code reviewer.
It keeps the correctness-critical parts **deterministic** (file selection, context assembly,
line-anchoring, severity gating, dedupe) and uses the LLM only for judgment (finding bugs,
proposing fixes). It runs five review ways:

- **Local review**: `miucr review` over a staged diff, a commit, or a ref range.
- **GitHub PR review**: `miucr review --pr` (dry-run by default; `--post` upserts ONE summary issue comment + posts inline comments as a PR review).
- **serve daemon**: HMAC webhook (default) and/or opt-in poll trigger; optional REST API + GitHub App auth.
- **MCP server**: `miucr mcp` exposes `review_run` / `review_get` over stdio to any agent host.
- **Evaluation**: `miucr eval` compares miu-cr and other reviewer commands against JSON expected findings.

**Review behavior worth knowing (design choices that prevent noise):**
- **One upserted summary, posted first.** `--post` writes ONE summary *issue comment*, edited in place on re-runs (never stacked), and posts it BEFORE the inline review so it anchors on top (overview → details). Inline findings are a separate PR review. `review_id` is NOT shown in the comment (it only resolves on the local store; it stays in the JSON envelope). On a **fatal review failure** (provider/network/auth, AFTER miucr's internal retries), `--post` upserts that SAME summary comment with a visible error notice instead of failing silently; a later successful run replaces it with findings.
- **The summary is a per-finding lifecycle ledger, not just the latest run.** Below a concise ≤5-bullet "What changed" summary, it renders two always-visible tracking tables — **⚠️ Open (N)** and **✅ Resolved (N)** — each finding tracked by its line-independent fingerprint across commits: a **Priority** column (P0–P4), status (`open` / `resolved` / `reopened`), the **origin commit** it was first raised on and the **resolved commit** it disappeared on (both linked), priority before→after for escalations, and first-seen / resolved timestamps. A clean review shows **Review passed · all clear 🎉** (not "No findings"). The footer is `Last reviewed commit` + review attempts + the miu-cr release. Lifecycle state is **storeless**: it lives in a hidden `<!-- miu-cr-ledger:<base64> -->` marker inside the comment (like the runs counter), so it survives ephemeral CI with no DB. A finding resolves only when it is absent AND its file is still in the diff (absence off-diff ≠ fix).
- **Inline comments persist; resolving the threads is left to you / your coding agent.** Each finding's inline comment is posted ONCE and deduped across re-runs via a hidden `<!-- miucr:fp=… -->` marker, so a re-review never re-posts or deletes it. miucr does NOT click "Resolve conversation": when a finding is fixed, GitHub auto-marks the thread *Outdated* and the summary ledger moves it to **✅ Resolved**, but the inline thread itself stays open for the developer/coding agent to resolve. A host config may opt into `thread_resolution_sync.mode: poll` to mirror manual GitHub "Resolve conversation" state into the summary (the Resolved row shows a clean `💬 conversation` marker linked to the discussion thread, distinct from a commit-resolved row's `open → resolved` SHA arrow); this never starts an LLM review and never feeds approval. So an agent acting on a review should read the inline threads, apply the fixes, reply on each handled inline thread with what changed and why, then resolve the thread.
- **Repeat-run stability is deterministic inputs + low-variance generation.** For the same repo/ref/config, file selection, context assembly, rules, anchoring, gating, fingerprints, and comment dedupe are deterministic. SDK-backed Anthropic/OpenAI calls use `temperature: 0`; exact model output can still vary, so PR posting is idempotent rather than duplicate-prone.
- **One-click suggestions and approvals are explicit write actions.** `--suggest` emits a native GitHub ` ```suggestion ` block ONLY for findings at or above the suggestion floor (`medium`) when the patch *deterministically* replaces the exact anchored line(s) and the model is certain of a grounded mechanical fix (a cited rule or an obvious best practice). It NEVER guesses an unverifiable value (a URL, path, route, ID, version, config key, API signature); such concerns become a verification-question in the rationale instead. `--patch-repair` (requires `--suggest`) runs one focused 2nd LLM pass to recover a repairable near-miss patch. `--approval clean|threshold` submits APPROVE only when the policy and safety gates pass; permission/self-approval failures warn and degrade rather than failing the review.
- **`-o pretty`** is the human-readable local format; **`-o json`** is for agents; `-o sarif` for editors/CI.
- **Multi-provider profiles.** Add a named provider (e.g. z.ai/glm) with `kind`, `base_url`, `model`, `auth`, and either `auth_env` or `auth_command`; select with `--provider <name>`. Built-in kinds: `anthropic`, `openai` (ChatGPT-plan OAuth via `miucr login`). Transient GitHub/network errors auto-retry with backoff. Optionally cap a provider instance's usage with `[providers.<name>.quota]` (`dimension = tokens|requests`, `limit`, `window = <Go duration like 5h/24h>|monthly`); **uncapped by default**, fail-closed, over-quota → typed `quota.exceeded`.
- **Thinking on by default; deterministic fallback.** Capable models (Claude, gpt-5/o-series, codex, **z.ai GLM 4.5+**) review with **extended thinking/reasoning** (deeper analysis; temperature is omitted because thinking forces temp 1). Models without thinking (gpt-4o, plain glm-4 chat) sample at **temperature 0** for stable, reproducible findings. Both are config-exposed: `[review].thinking` (`auto|off|low|medium|high`, default auto) and `[review].temperature` (0–2, default 0). Set `MIUCR_TRACE_REASONING=true` to capture that reasoning into the review trace (`miucr trace <id>`).

## Output contract: `miucr.cli/v1` envelope (parse this)

Every command prints **one JSON object** on stdout (default `-o json`). Field order:

```json
{
  "ok": true,
  "api_version": "miucr.cli/v1",
  "kind": "review.result",
  "command": "review",
  "request_id": "req_...",
  "summary": { "findings": 2, "gate": "high" },
  "data": { "...": "command-specific" },
  "artifacts": [],
  "warnings": []
}
```

- `ok` (bool) is the branch point. `artifacts` and `warnings` are **always present** (`[]` when empty).
- `summary`, `data`, `page`, `stats` are present only when relevant (`omitempty`).
- Errors use the **same envelope** with `ok:false`, `kind:"error"`, and an `error` object:

```json
{ "ok": false, "api_version": "miucr.cli/v1", "kind": "error", "command": "review",
  "error": { "code": "review.gate_failed", "message": "<redacted>", "hint": "...",
             "retryable": false, "safe_to_retry": false } }
```

`kind` per command: `version`, `review.result`, `config.show`, `rules.check`, `rules.init`, `init.result`, `login.result`,
`whoami`, `logout`, `history.list`, `history.record`, `history.prune`, `eval.result`, `trace.show`, `error`
(REST: `review.accepted` / `review.result`). **Secrets never appear** in the envelope, logs, or on disk
(credential-named fields are scrubbed; finding `rationale`/`suggested_patch` prose is exempt).
The `--instruction`/`--conversation` flags and the `/miucr review <prompt>` comment trigger only add
**input** (a USER-turn context block); they never change the envelope or the finding JSON (still
`miucr.cli/v1`); parse the same shape.

### Exit codes (gate → exit mapping)

| Exit | Meaning |
| ---- | ------- |
| `0`  | Success: no finding reached `--gate`. |
| `1`  | Operational error: missing credentials, internal failure, store unavailable. |
| `2`  | **Gate failed** (a finding's severity ≥ `--gate`) **or** invalid invocation (bad gate, conflicting/zero modes, bad `--output`). |

Severities low to high: `info` < `low` < `medium` < `high` < `critical`. A `review.gate_failed`
error is emitted *after* the normal `review.result` envelope (the findings still print), then exit 2.

### Typed error codes (branch on `error.code`)

The day-1 provider/auth/timeout failures classify into a **stable taxonomy** (same code across all backends: anthropic/openai/codex), each with an actionable `hint` and a correct `retryable`:

| `error.code` | When | `retryable` | Hint |
| ------------ | ---- | ----------- | ---- |
| `agent.auth_failed` | bad/invalid API key (401/403, api-key backends) | `false` | `miucr login …` / set a valid key |
| `agent.auth_expired` | expired OAuth (401/403; codex incl. still-401-after-refresh) | `false` | `miucr login --provider openai` |
| `provider.rate_limited` | 429 | `true` | wait for the reset window and retry |
| `agent.unavailable` | 5xx / 529 | `true` | retry shortly |
| `review.timeout` | the review exceeded `--timeout` | `true` | raise `--timeout` (e.g. `1800s`) or narrow the diff |
| `review.canceled` | ctx canceled (Ctrl-C / SIGINT), exit `130` | `false` | - |
| `config.invalid` | malformed `config.toml` / bad enum or `auth` value / an `openai`-kind gateway profile with a key but no `base_url` (exit `2`; same code across review/history/serve) | `false` | fix the named field / set `base_url` for the gateway profile |
| `quota.exceeded` | the resolved provider's `[providers.<name>.quota]` is exhausted for the current window; exit `2`. On the serve host the PR is skipped+logged, not failed (a later push re-checks). A quota counter that can't be read/opened fails closed as the retryable `store.unavailable` instead (serve retries, not skips) | `false` | raise the provider quota `limit` or wait for the window to reset |
| `github.auth` | PR fetch hit `401`/`403` (bad/missing `GITHUB_TOKEN` or insufficient scope) | `false` | check `GITHUB_TOKEN` / its repo scope |
| `github.pr_not_found` | PR fetch hit `404` (no such PR, or the token can't see it) | `false` | check the PR exists and the token has access |
| `github.rate_limited` | PR fetch hit `429` (REST rate limit or abuse-detection) | `true` | GitHub rate limit: wait for the reset and retry |
| `github.unavailable` | PR fetch hit `5xx` / a network error (DNS / refused / timeout) | `true` | GitHub unavailable / unreachable, retry shortly |
| `github.pr_fetch_failed` | any other unclassified PR-fetch failure | `false` | - |
| `internal.error` | any unclassified failure (default; bare-wrapped) | `false` | - |

Unknown failures stay `internal.error` (never mislabeled as retryable). Classified messages are redacted: **no token fragment ever appears**.

The **codex** backend retries `429`/`502`/`503`/`504` (and a `response.failed` stream event) with bounded, jittered exponential backoff (≤3 attempts) like the SDK backends, honoring `Retry-After`/`resets_in_seconds` and aborting on cancel/timeout. A persistent rate limit returns `provider.rate_limited` with the usage-cap reset window in `error.details.resets_in_seconds` (or `retry_after_seconds`); branch on that to decide wait-vs-switch-provider.

## Install

```sh
curl -fsSL https://cr.miu.sh/install.sh | sh   # asset-aware latest
curl -fsSL https://cr.miu.sh/install.sh | sh -s -- v0.65.0   # pin
brew install vanducng/tap/miucr                                                     # Homebrew
go install github.com/vanducng/miu-cr/cmd/miucr@latest                              # Go 1.25+
```

Verify: `miucr version` → `{"ok":true,...,"data":{"version":"v0.65.0"}}`.
Config (optional) at `~/.config/miu/cr/config.toml`; state DB at `~/.config/miu/cr/state.db`.
Repo rules at `.miu/cr/rules/*.md` (**never a flat `.miucr/`**).

## Onboarding (`miucr init`)

`miucr init` is the fastest path to a working config. It walks a clean, sectioned
wizard (**provider → provider-aware auth → project rules**), then writes
`~/.config/miu/cr/config.toml` (dir `0700`, file `0600`, **deltas only**: the
chosen provider block, never the full built-in defaults) and ends on the literal
`miucr review --staged`.

```sh
miucr init                                  # interactive wizard (idempotent: Overwrite? y/N)
miucr init --non-interactive --provider anthropic --auth-env ANTHROPIC_API_KEY --yes
```

- **Provider-aware auth menu**: `openai` offers **browser login (OAuth, default)**
  (review on your ChatGPT/Codex plan, no API key) plus env-var or paste; it runs
  the same PKCE loopback flow as `miucr login` and caches the token in `oauth.json`
  (config records just `default_provider = "openai"`, no secret). `anthropic` offers
  env-var (default) or paste, **no OAuth** (Anthropic ToS). `custom` asks kind +
  base URL, then env-var or paste.
- **Default writes no secret**: only the env-var **name** (`auth_env`). A literal
  `auth_token` lands only on explicit paste + confirm (after a plaintext-on-disk warning).
- Flags: `--provider anthropic|openai|custom`, `--auth oauth|env|paste` (non-interactive
  selector), `--auth-env <NAME>`, `--base-url <gateway>`, `--no-rules`, `--force`,
  `--yes`, `--non-interactive`. `--auth oauth` is interactive-only (needs a browser);
  non-interactive errors `init.aborted` toward `miucr login`. Envelope `kind: init.result`
  (`data.auth_method` = `oauth|env|paste`, `data.next` = `miucr review --staged`); errors
  `init.aborted` / `config.write_failed`.
- `init` is **optional**: zero-config still works when a provider key is on the env.
  With no config **and** no key, `review` prints a soft one-line nudge to run `init`.

## Examples (copy-paste starters)

The repo ships an [`examples/`](https://github.com/vanducng/miu-cr/tree/main/examples)
tree: `rules/{go-api,typescript-node,python-data}.md`,
`github-action/code-review.yml` (fork-safe `pull_request_target`),
`workflows/miucr-review.yml` (the **dual-trigger** default: `pull_request` + a
`/miucr review <prompt>` comment trigger),
`mcp-setup/{claude-code,cursor,codex}` + `README-mcp.md`,
`review-local/{pre-commit,Makefile,agent-review.sh}` (review-your-own-changes
recipes), and `review-host/{Dockerfile,docker-compose.yml,config.example.yaml}`
(pure-Go `CGO_ENABLED=0` Alpine image + Postgres host stack for `miucr serve`).
Onboarding walkthrough lives at the docs
[Getting started](https://cr.miu.sh/onboarding/) page.

**Comment-triggered review (`/miucr review <prompt>`).** With the dual-trigger workflow
installed, a **write or admin collaborator** posts `/miucr review <prompt>` as a top-level PR
comment (e.g. `/miucr review focus on the auth changes`) to steer a re-review with free text.
The `issue_comment` event runs the trusted base-branch workflow with full secrets even on
fork PRs, so the workflow self-gates: the commenter must have **write|admin** (an
`actions/github-script` `repos.getCollaboratorPermissionLevel` check; `author_association`
alone is insufficient), the comment body is read via an env var (never inline-interpolated
into `run:`), the released binary is used (fork head code is never built with secrets), and
miucr adds a 👀 reaction to acknowledge an accepted command. Known limits (v1): only
top-level `issue_comment` is caught (not inline review comments or review summaries), and an
unchanged head SHA short-circuits (there is no `--force` on the comment path yet).

## Commands & exact flags

Global flags (all commands): `-o, --output json|pretty|sarif` (default `json`), `--timeout <dur>`
(default `30s`; `review` auto-bumps to `900s` and `eval` to `30m` unless `--timeout` is set explicitly).
`sarif` is **review-only**: it emits a SARIF 2.1.0 document (NOT the envelope) for
code-scanning/IDEs (`ruleId`=category, `level` from severity, repo-relative paths);
upload it with `github/codeql-action/upload-sarif`. `pretty` is a local reporter
(jumpable `file:line`, excerpt, patch; color on a TTY). `review --pr` also takes
`--filter-mode added|diff_context|file|nofilter` (default `diff_context`) controlling
which findings are inline-eligible; `file`/`nofilter` route off-diff findings to the
summary/SARIF/local output, never inline.

### `review`: needs **exactly one** mode

```sh
miucr review --staged                     # staged changes vs the index
miucr review --from main --to HEAD        # ref range (--from and --to required together)
miucr review --commit HEAD~1              # one commit vs its parent
miucr review --pr owner/repo#123          # a GitHub PR (dry-run by default)
miucr review --staged --instruction "focus on the auth changes"   # steer this one review
miucr review --pr owner/repo#123 --conversation                   # also read the prior PR thread
```

| Flag | Default | Notes |
| ---- | ------- | ----- |
| `--staged` | off | Review the **index** (what you're about to commit), not HEAD. |
| `--from` / `--to` | - | Range mode; **required together**. |
| `--commit <ref>` | - | Single commit vs first parent. |
| `--pr <url\|owner/repo#N>` | - | GitHub PR; `https://github.com/owner/repo/pull/N` or `owner/repo#N`. |
| `--gate none\|info\|low\|medium\|high\|critical` | `high` | Exit 2 when a finding reaches this severity. `none` never fails. |
| `--repo <dir>` | `.` | Repository directory. |
| `--include` / `--exclude` | - | Repeatable doublestar globs (path must match / drop). |
| `--ext go,ts,...` | - | Restrict to these file extensions. |
| `--expand <n>` | `5` | Context lines above/below each hunk (`0` disables). |
| `--token-budget <n>` | `0` | Approx token budget; over budget degrades context (`0` disables, so the default is no cap). |
| `--deep-context` | OFF | Heavier file context for large reviews: `--expand 20`, `--token-budget 0`, `--timeout 900s`, auto related-file hop depth, and root `AGENTS.md` / `CLAUDE.md` from the reviewed revision unless those flags are set. |
| `--context-hops <n>` | `0` | Override related-file context depth from changed files (`0` disables, max `5`); follows Go package imports/reverse imports and basic relative JS/TS/Python imports from the reviewed revision. Skipped on fork PRs. |
| `--provider anthropic\|openai\|<name>\|auto` | `auto` | LLM profile. |
| `--api-key` / `--base-url` / `--auth-token` / `--model` | - | Provider overrides; **never persisted**. |
| `--token <pat>` | - | GitHub PAT (overrides `GITHUB_TOKEN`/`GH_TOKEN`); required only for `--post`; never persisted. |
| `--post` / `--no-post` | `--no-post` (for `--pr`) | Publish vs dry-run; mutually exclusive (`flags.conflict`). |
| `--suggest` | OFF | Native one-click suggestions for proven fixes at or above `medium`: single-line replacements, contiguous range replacements, and wrap/guard/insert fixes on a QuotedCode-proven single-line anchor; requires `--post`; author-applied, never pushed. |
| `--patch-repair` | OFF | Conditional **2nd LLM pass** that recovers one-click suggestions the first pass *almost* produced: for each single-line finding `>= medium` whose `SuggestedPatch` was rejected for a *repairable* reason (empty / no-op / length mismatch — never a true anchor mismatch), one focused agent call asks for a minimal replacement of the verbatim anchored span, then **re-validates with the same exact-anchor gate**; emits the suggestion only if it now passes, else keeps the fenced hint. **Requires `--suggest`** (`config.invalid`, exit 2, otherwise); inert in dry-run (recovers only on `--post`). Bounded: per-review cap (default 5), highest-severity-first; one extra LLM call per repaired candidate. PR-path only, default OFF. |
| `--approval off\|clean\|threshold` | `off` | Submit `Event=APPROVE` by policy on `--pr --post`. `clean` requires zero findings; `threshold` allows findings at or below `--approval-max-priority`. Permission/self-approval failures warn and degrade. |
| `--approval-max-priority P0\|P1\|P2\|P3\|P4` | `P4` | Threshold approval ceiling. `P3` approves P3/P4 only; P0-P2 block approval. |
| `--approval-note none\|on_findings\|always` | mode default | Controls approval review body text. `threshold` defaults to `on_findings`; clean approvals default to silent. |
| `--filter-mode added\|diff_context\|file\|nofilter` | `diff_context` | Inline-eligibility filter on `--pr`. `file`/`nofilter` route off-diff findings to summary/SARIF/local, never inline (GitHub 422s an off-diff comment). |
| `--min-severity none\|info\|low\|medium\|high\|critical` | none (no floor) | Minimum severity posted **inline** on `--pr`. Below-threshold findings still appear in the summary header counts + SARIF, never inline. An out-of-set value is rejected (`flags.invalid_min_severity`, exit 2). |
| `--walkthrough-diagram` | OFF | Opt in to a Mermaid change diagram in the summary (fenced ```mermaid block GitHub renders). Rides the same single review pass, no extra LLM call. Diagram quality varies; a malformed/omitted diagram degrades to a plain note. |
| `--mode review\|checks` | `review` | GitHub reporter on `--pr --post`. `review` posts inline comments + a summary. `checks` posts a GitHub CheckRun with annotations (survives force-push, works on fork PRs, can be a **required** check); conclusion maps from the gate (gate-clean→`success`, gate-hit→`failure`); needs `checks: write`. |
| `--format full\|minimal` | `full` | Review-comment presentation on `--pr`. `full` is the current output (summary section + severity/priority badges). `minimal` drops the `## Code Review Summary` section and **all** shields badges (summary chips **and** the per-finding inline `P3 · bug`), keeping inline findings, the footer, and the hidden upsert markers. Render-only — does not change which findings surface. An out-of-set value is rejected (`flags.invalid_format`, exit 2). |
| `--prompt-format xml\|markdown` | `xml` | Review **prompt** structure (orthogonal to `--format`, which is comment presentation). `xml` (the default) wraps untrusted payloads (diffs, new-content, project files, rules, conversation) in entity-escaped XML tags instead of `===`/`---` delimiters + fences, hardening against delimiter-collision / prompt-injection (a planted `</file>` or `=== File: ===` stays inert). `markdown` is the prior fenced form (byte-identical to ≤0.65), available as opt-out. Out-of-set value rejected (`flags.invalid_prompt_format`, exit 2). Also `[review].prompt_format`. |
| `--sarif-out <path>` | - | Also write a SARIF 2.1.0 report to `<path>` from the SAME single review run (in addition to `--output`/posting). Written only on success (atomic temp+rename); a failed run leaves no file. This is how the Action does single-pass SARIF, no second LLM call. |
| `--no-save` | off | Skip persisting this run to the local history store (every review is saved by default). |
| `--force` | off | On `--pr`, re-review even when the head SHA is unchanged since the last saved review. By default an unchanged head SHA short-circuits (`skipped_unchanged`, no LLM pass); a new commit always re-reviews. |
| `--instruction <text>` | - | Free-text steer for **this** review (e.g. `"focus on the auth changes"`). Injected into the **USER turn** as a fenced, context-only block; it never changes the finding rules, severity, category, or JSON schema, and rides the same single review pass (no extra LLM call). Trusted (developer-authored CLI flag); still UNTRUSTED when set from an `issue_comment` trigger on a fork PR. |
| `--conversation` | off | On `--pr`, fetch the prior PR conversation (miucr's summary + finding threads + developer replies) and inject it fenced/context-only as **UNTRUSTED** context (dropped on fork PRs). One extra GitHub **read** pass, no extra LLM call. |
| `-v, --verbose` / `-q, --quiet` | auto | Progress to **stderr** (stdout envelope unchanged). Auto-on when stderr is a TTY; `-v` forces on, `-q` forces off; mutually exclusive. Piped/CI stays silent. |
| `--trace` | off | Stream the live review trace (system prompt, diff, rules, prompts, response) as NDJSON to **stderr** (local-only, redacted; distinct from `--verbose`; stdout envelope unchanged). Inspect a saved review's trace with `miucr trace <id>`. |

**`review.result` data** (local and `--pr`):

```jsonc
"data": {
  "findings": [
    { "file": "internal/foo/bar.go", "line": 42, "end_line": 42,
      "title": "…optional short scannable summary…",   // omitted when the model emits none
      "rule": "go",                                     // optional: stem of the project rule that motivated this finding (omitted when none)
      "severity": "high", "category": "bug",
      "rationale": "…why this is a problem (may cite a convention the model can see, e.g. \"differs from mapWriteError\")…",
      "suggested_patch": "…optional minimal fix…",
      "quoted_code": "…verbatim source the finding anchors to…" }
  ],
  "stats": { "files_changed": 3, "files_reviewed": 2, "findings_total": 2,
             "findings_dropped": 1, "max_severity": "high", "gate": "high",
             "truncation_level": "full",            // full | hunks_only | filenames_only
             "rules_applied": 5, "rules_truncated": false },
  "review_id": "rev_...",  // additive: the saved history record id ("" only with --no-save; on an incremental skip it is the prior review id)
  // additive, only on a --pr run when an unchanged head SHA short-circuited (no
  // LLM pass). Dry-runs skip from the local history store; --post can skip from
  // the completed-publish marker in the summary comment. Both fields are omitted
  // on a normal review. On the skip path findings is [] and stats is {} (never null):
  "skipped_unchanged": true, "prior_review_id": "rev_prior",
  "pr": {  // only on --pr
    "owner": "owner", "repo": "repo", "number": 123, "head_sha": "deadbeef",
    "is_fork": false, "posted": false, "posted_inline": 0,
    "summary_action": "none",         // fate of the ONE upserted summary issue comment: none | created | edited | fork_fallback | failed
    "approve_action": "commented", "approve_reason": "not_requested", "suggestions_posted": 0,
    "patches_repaired": 0,            // additive, omitempty: findings whose rejected SuggestedPatch the --patch-repair 2nd pass recovered into a now-clean one-click suggestion (0/absent when --patch-repair is OFF)
    // additive, omitted when empty:
    "mode": "review",                 // review (default) | checks
    "check_run_id": 0, "check_conclusion": "",  // --mode checks only (success|failure)
    "fallback_annotations": 0 }       // >0 when a fork-PR 403 under Actions fell back to ::error:: workflow annotations (review did NOT hard-fail); summary_action then "fork_fallback"
}
```

`findings_dropped` = findings rejected by line-anchor drift (their quote no longer matches the reviewed
revision, kills position drift). `--post` keeps the summary and the inline findings in **separate
homes**: inline comments post as a PR **review** (body left empty, never a 422 on a no-inline run), and
the summary is **ONE issue comment that is UPSERTED**: miu-cr lists the PR's issue comments, finds the
one carrying the `<!-- miu-cr-review -->` marker, and **edits it in place**; if none exists it creates it.
So a re-run **updates the single summary** instead of stacking a review per commit. `summary_action` is
`created` (new summary issue comment), `edited` (upserted in place), `fork_fallback` (a fork PR lacked
comment-write scope, degraded, no hard fail), `failed` (summary upsert failed after inline posting), or
`none` (`--no-post`, `--mode checks`, or a clean no-summary run). A same-commit `--post` re-run
short-circuits after a matching completed-publish marker; pass `--force` to review anyway.
per-comment `<!-- miucr:fp=... -->` line-free fingerprints prevent inline dupes across commits. The
summary body itself carries a **finding lifecycle ledger** — Open + Resolved tables with per-finding
status/origin+resolved commit/priority-before→after/timestamps — persisted storelessly in a hidden
`<!-- miu-cr-ledger:<base64> -->` marker so the open/resolved history survives across pushes (and
ephemeral CI) without a DB. The `miucr.cli/v1` JSON envelope is unchanged: the ledger is a
rendering/comment concern, not an envelope field.
A public-PR dry-run needs **no GitHub PAT** (LLM key still required); `--post` and private repos need a PAT with `repo` scope.

### `serve`: webhook daemon (default) + opt-in poll

```sh
WEBHOOK_SECRET=… GITHUB_TOKEN=… ANTHROPIC_API_KEY=… \
  miucr serve --addr :8080 --repos owner/repo,owner/other --gate high
```

| Flag | Default | Notes |
| ---- | ------- | ----- |
| `--addr` | `:8080` | Webhook listen address. |
| `--gate` | `high` | **Publish-severity only**: which findings get posted; never affects liveness/exit. |
| `--repos` | - | **Required** owner/repo allowlist (comma-separated); other repos are ignored. |
| `--poll` | off | Opt-in trigger: periodically ask GitHub which PRs need review. Webhook stays default. |
| `--poll-interval` | `1m0s` | Floor; effective = `max(this, X-Poll-Interval)`. |
| `--poll-source notifications\|pulls` | `notifications` | Candidate source. `pulls` = full coverage / cold-start-complete. |

Env: `WEBHOOK_SECRET` (required unless poll-only), `GITHUB_TOKEN`/`GH_TOKEN` (required unless `[github] mode=app`),
`ANTHROPIC_API_KEY` (or compatible). `MIUCR_LOG_LEVEL=debug` enables progress/tool-turn logs; `MIUCR_TRACE_LOG=true`
adds bounded debug trace payloads (`MIUCR_TRACE_LOG_MAX_BYTES`, default `4096`) that are redacted/truncated but may
include prompt/diff context. `MIUCR_TRACE_REASONING=true` captures the model's reasoning as a `reasoning` trace step
(Claude/GLM thinking verbatim; OpenAI a token count + `[hidden by provider]`) — off by default, redacted in storage,
needs `[review].thinking` on. Endpoints: `POST /webhook` (HMAC), `GET /healthz`. Each new head SHA = one full
LLM review; allowlist + per-head dedup are the only spend guards. serve inherits `--suggest` **OFF** and `review.approval.mode: off`.

In `serve --host` YAML, `thread_resolution_sync` is an object and defaults off. Enable it per repo when manual GitHub
conversation resolution should update the summary table between commits:

```yaml
review:
  thread_resolution_sync:
    mode: poll
    interval: 5m
```

**Opt-in REST API**: set `MIUCR_API_TOKEN` (env-only, no flag) to register `/v1`:

```sh
MIUCR_API_TOKEN=$(openssl rand -hex 32) WEBHOOK_SECRET=… GITHUB_TOKEN=… ANTHROPIC_API_KEY=… \
  miucr serve --addr :8080 --repos owner/repo
# Queue (202 + server-generated crypto/rand id):
curl -sS -X POST https://host/v1/reviews -H "Authorization: Bearer $MIUCR_API_TOKEN" \
  -H 'Content-Type: application/json' -d '{"owner":"acme","repo":"widgets","number":42}'
# Read back (whitelist: id,status,created_at,findings,stats, never the clone path):
curl -sS https://host/v1/reviews/<id> -H "Authorization: Bearer $MIUCR_API_TOKEN"
```

Status lifecycle: `pending` → `done`/`failed`. HTTP map: `400` bad body, `401` missing/wrong bearer
(empty token can never auth), `403` off-allowlist, `404` unknown id, `405` wrong method, `413` body > 64 KB.
**Single-operator**: one shared bearer = one trust boundary (not multi-tenant).

**GitHub App auth** (opt-in alternative to PAT): `[github] mode=app` in config (see below).

**Host mode**: `miucr serve --host` loads YAML from `MIUCR_CONFIG` or
`~/.config/miu/cr/host.yaml`, requires Postgres (`store.backend: postgres`;
`MIUCR_PG_DSN` preferred), and watches multiple repos from one daemon. Validate
without opening DB/secrets:

```sh
MIUCR_CONFIG=examples/review-host/config.example.yaml miucr serve --host --dry-run-config -o json
```

Dry-run emits envelope kind `serve.host_config` with a redacted config plus
summary counts (`repos`, `accounts`). Host YAML uses `providers`, `store`,
`github.accounts`, top-level `review`/`agent`, `host.review`, and `repos[]`;
layering is defaults -> `review`/`agent` -> `host.review` -> repo overrides.
PAT accounts support `auth_env`/`auth_file`/`auth_command`; App accounts support
App/installation ids from literal/env plus private keys from path/env/command.
Provider credentials also support `auth_env` and `auth_command`.

Repo prompts override the global prompt (`system_prompt` or
`system_prompt_file`, mutually exclusive). `repos[].rules` can point to markdown
files or a non-recursive directory of `*.md`; these are trusted host context and
cannot change the protected finding schema. Host review write policy lives at
the effective repo level: `post`, `force`, `suggest`, `patch_repair`,
`thread_resolution_sync`, and `approval`. First host mode does not push code.

Host poller state lives in Postgres: repos, PR sessions, queued jobs, attempts,
workspaces, poll cursors, and retention metadata. Startup applies versioned
schema migrations under an advisory lock. Claims use row locks for concurrency,
and `host.retention` prunes old jobs/attempts/sessions/workspace records/cursors.
The review-host compose example defaults `MIUCR_LOG_LEVEL=debug` for local
dogfood while leaving `MIUCR_TRACE_LOG=false`.

`review.pr_filter` layers top-level -> `host.review` -> `repos[].review`.
Draft PRs are skipped unless `include_drafts: true`. `default_action` defaults
to `include`; set `default_action: exclude` for allowlist repos. Rules are
evaluated in order and the last matching rule wins. Matchers inside one rule are
ANDed. Supported matchers: `authors`, `author_types` (`Bot`, `User`,
`Organization`), `author_associations`, `title_regexes`, `labels`,
`requested_reviewers`, `base_branches`, and `head_branches`. Use title regexes
for generated PRs that may be opened by a human token, such as `^chore\(deps\):`.
`comment_trigger_regexes` are used by the GitHub Action comment-trigger workflow,
not by `serve --host poll_source: pulls`.

```yaml
review:
  pr_filter:
    default_action: include
    include_drafts: false
    comment_trigger_regexes:
      - '(^|\s)(/miucr review\b|@vanducng\b)'
    rules:
      - action: exclude
        title_regexes: ['^chore\(deps\):']

repos:
  - name: critical-dbt
    slug: example-org/critical-dbt
    review:
      pr_filter:
        default_action: exclude
        rules:
          - action: include
            authors: ["vanducng"]
          - action: include
            requested_reviewers: ["vanducng"]
```

### `rules`: project review context

```sh
miucr rules init             # scaffold annotated .miu/cr/rules/example.md
miucr rules init --force     # overwrite
miucr rules check internal/foo/bar.go   # which loaded rules apply to a path (kind: rules.check)
```

Rule files are markdown with YAML frontmatter, then prose injected as **context only** (never gate):

```markdown
---
description: Project-specific review context for changes under cmd/.
globs:
  - "cmd/**/*.go"
  - "internal/**/*.go"
alwaysApply: false
context_files:
  - "AGENTS.md"
---
# Prose below the fence is injected as CONTEXT for the reviewer.
```

Three layers merged by **file stem** (later overrides earlier): built-in defaults (Trusted, lowest) →
user `~/.config/miu/cr/rules/*.md` (Trusted) → repo `.miu/cr/rules/*.md` (**Untrusted**, highest).
A file with **no `---` fence is skipped** (never always-applied). Untrusted repo rules are fenced
context-only, byte-capped, and **dropped on fork PRs**; the finding-JSON schema stays in the cached
system prompt so injected prose can't redefine it. `rules check` data lists each applicable rule with
`provenance`, `stem`, `globs`/`always_apply`, `trusted`, plus skipped `body_only` files.

**Rule grounding.** A finding may carry the `rule` stem of the project rule that motivated it. The
wire layer validates the stem against the rules actually loaded this review (a hallucinated stem is
dropped) and renders it as `(per <stem>)` on the inline comment + summary overflow. A repo rule
(`.miu/cr/rules/*.md`) additionally links to its file, repo-relative at the head SHA; user and
built-in rules are cited as text only (no link, a user-rule home path never leaks).

### `history`: browse saved reviews

Every review auto-saves a **full record** (findings + stats + per-turn transcript + raw prompt/response)
to the local store; `--no-save` opts out per run. Records are local only (`~/.config/miu/cr/state.db`,
gitignored); **no tokens are ever stored**.

```sh
miucr history                                 # list recent reviews, newest first (kind: history.list)
miucr history --repo owner/repo               # filter by repo (PR) or repo dir (local)
miucr history --pr owner/repo#7               # filter to one PR
miucr history --since 7d                       # 7d / 24h / 2026-06-01
miucr history --limit 50                        # cap rows (default 20; 0 = no limit)
miucr history show <id>                         # one full record (kind: history.record; 404 → history.not_found)
miucr history show <id> -o pretty --raw         # pretty, with raw prompt/response inline
miucr history prune --keep 200 --yes            # keep newest N (kind: history.prune; reports deleted count)
miucr history prune --older-than 30d --yes      # delete records older than a span
```

`prune` needs at least one of `--keep`/`--older-than` plus `--yes` (destructive). An optional
`[history] max_records = N` auto-prunes oldest on save. List rows carry
`{id, created_at, target, mode, findings, max_severity, status}`; `show` data adds
`provider`, `model`, `head_sha`, `findings`, `stats`, `transcript`, `raw_prompt`, `raw_response`.
Errors: `history.unavailable`, `history.not_found`, `history.prune_policy_required`,
`history.prune_confirm_required`, `history.bad_pr`, `history.bad_time`.

### `eval`: compare reviewer quality against expected findings

`miucr eval` runs one or more reviewer commands over a JSON suite and scores them by
file+line overlap against expected findings. Use synthetic/public fixtures only.
For unlabeled public-PR smoke suites, read unmatched findings as review output to
inspect, not as confirmed invalid findings.

```json
{
  "cases": [
    {
      "id": "go-sql-injection",
      "repo": "/tmp/review-fixtures/go-api",
      "from": "clean",
      "to": "buggy",
      "expected": [
        { "id": "sql-injection", "file": "internal/users.go", "line": 42, "severity": "critical", "category": "security" }
      ]
    }
  ]
}
```

```sh
miucr eval --cases eval.json \
  --tool 'miucr=miucr review --repo "$MIUCR_EVAL_REPO" --from "$MIUCR_EVAL_FROM" --to "$MIUCR_EVAL_TO" --gate none --deep-context --no-save -o json' \
  --tool 'other=./scripts/run-other-reviewer-json "$MIUCR_EVAL_REPO" "$MIUCR_EVAL_FROM" "$MIUCR_EVAL_TO"' \
  --timeout 30m
```

Each tool command runs once per case with `MIUCR_EVAL_CASE_ID`, `MIUCR_EVAL_REPO`,
`MIUCR_EVAL_FROM`, `MIUCR_EVAL_TO`, and `MIUCR_EVAL_COMMIT` set. The command must
print either a normal `miucr review` envelope or `{"findings":[{"file":"...","line":1}]}`.
Tool commands run from the case repo, so use `PATH` commands or absolute paths for
repo-local scripts/binaries.

Reusable local benchmark:

```sh
reports_dir="${VD_REPORTS_PATH:?set by session hook}/miucr-eval"
scripts/eval/materialize-fixtures.sh --cases testdata/eval/miucr-quality.json --out "$reports_dir/fixtures"
# testdata/eval/public-prs.json is unlabeled; use it for runtime/finding-volume review.
MIUCR_BIN=/absolute/path/to/miucr scripts/eval/run-public-pr-benchmark.sh --cases testdata/eval/public-prs.json --out "$reports_dir/public-prs" --limit 20 --timeout 30m
```

`eval.result` data is `{tools:[{name, summary, cases}]}`. Scores include `expected`,
`found`, `matched`, `missed`, `false_positives`, `precision`, `recall`, `f1`,
`duration_ms`, and `failed_cases`. Per-case `stats` preserves reviewer stats such as
`context_ms` and `provider_ms` when the tool prints a `miucr review` envelope.
Duplicate findings count as false positives.

### `trace`: inspect a review's full trace

Every saved review keeps a **redacted trace** (system prompt, diff identification, selected files,
injected rules, user prompt, model/provider, raw response, tool calls). `miucr trace <id>` renders it
as ordered steps. The trace holds the prompt (your own code) so it is **local only**: read from the
history store, never re-fetched from a provider, never posted, and never in the `review.result`
envelope; secrets are redacted at persist.

```sh
miucr trace <id>                 # ordered steps (kind: trace.show; 404 → trace.not_found)
miucr trace owner/repo#123       # resolves to that PR's most recent saved review
miucr trace <id> -o pretty       # readable per-step view
```

`trace.show` data is `{id, steps:[{step, payload}]}` ordered: `system_prompt` → `diff_meta` →
`selected_files` → `injected_rules` → `user_prompt` → `model` → `final_response` → `tool_calls`
(empty steps omitted; an old review with no trace renders empty). Errors: `trace.id_required`,
`trace.not_found`, `trace.corrupt`.

For a **live** trace, pass `--trace` to `review`: each capture seam streams one NDJSON line
(`{"step":...,"payload":...}`) to **stderr** as the run proceeds (local-only, redacted; distinct from
`--verbose`). The stdout result envelope is byte-for-byte unchanged.

### `mcp`: review engine over stdio

```sh
miucr mcp                       # stdio transport (default)
miucr mcp --transport stdio
```

Reviews the repo in the **current working directory**: launch from (or point the host at) the target repo.
Stdout carries only MCP frames; logs/errors go to stderr. Tool outputs are byte-bounded (1 MiB) → oversized
fails `review.output_too_large` (narrow the review).

- **`review_run`**: args `{ staged, from, to, commit, gate, expand, token_budget, instruction }` (exactly one
  mode, same validation as the CLI). Optional `instruction` is a free-text steer injected fenced/context-only
  into the USER turn; it never changes the finding schema (UNTRUSTED, context-only). Returns
  `{ id, findings, stats }`; `id` is the persisted review id.
- **`review_get`**: args `{ id }`. Returns `{ id, repo_dir, mode, head_sha, created_at, findings, stats }`.

Register in Claude Code: `claude mcp add --transport stdio miucr -- miucr mcp --transport stdio`
(provide a provider key via the host's `env`, e.g. `ANTHROPIC_API_KEY`).

### `login`: OAuth to review on your ChatGPT plan

```sh
miucr login --provider openai     # PKCE loopback OAuth; caches token at ~/.config/miu/cr/oauth.json (0600)
miucr login --no-browser          # headless/SSH: print the authorize URL instead of opening a browser
```

Reviews authed by this token route to the **codex backend** (`chatgpt.com/backend-api/codex`,
Responses protocol) so they run on the user's **ChatGPT Pro/Max subscription**, not a billed key.
On this path the model defaults to `gpt-5.5` (the codex backend rejects api.openai.com models like
`gpt-4o`); `miucr init` writes `model = "gpt-5.5"` into `[providers.openai]` so it is visible + editable.
Precedence: `--model` > `MIUCR_CODEX_MODEL` > the config `model` (if not `gpt-4o`) > `gpt-5.5`.
`--provider` is an explicit flag backed by a registry; `openai` is the only entry
(`--provider anthropic`/unknown → `login.provider_unsupported`; Anthropic OAuth is ToS-prohibited).
Loopback binds an allow-listed port (`1455`, then `1457`). Envelope `kind: init.result`-style
**secret-free** payload: `{provider, oauth_path, expires_at, account_id, has_api_key}` (**no tokens**).
Errors: `login.provider_unsupported`, `login.port_unavailable`, `login.timeout`, `login.exchange_failed`, `login.write_failed`.

**Precedence**: the cached OAuth credential sits **below** an explicit `--api-key` / `OPENAI_API_KEY`
in OpenAI resolution: an explicit key always wins; OAuth is consulted only when no OpenAI key is set.
`oauth.json` is gitignored, `0600`, never logged/in-envelope.
**CI uses an `OPENAI_API_KEY` secret, not OAuth** (browser-interactive): `miucr review --provider openai`.

### `whoami` / `logout`: inspect and clear the cached OAuth identity

```sh
miucr whoami     # {logged_in, provider, account_id, expires_at, expired} (NEVER the token)
miucr logout     # delete oauth.json; idempotent ({removed: bool})
```

`whoami` whitelists only the non-secret fields from the cached record: the four secret fields
(access/refresh/id token, api key) are never read into the envelope, so no token can leak (json or
pretty). No cached record → `kind: whoami` with `{logged_in: false}` (clean exit, not an error).
`logout` removes `oauth.json`; a missing record reports `{removed: false}` rather than erroring, so
it is safe to run twice. Both emit the `miucr.cli/v1` envelope (`kind: whoami` / `kind: logout`).

### `upgrade` (alias `update`): self-update from GitHub Releases

```sh
miucr upgrade            # download + verify + atomically replace the running binary
miucr upgrade --check    # report only whether a newer version exists (no download)
miucr upgrade --version v0.13.0   # install a specific tag instead of latest
```

Resolves the latest release tag (honors `GITHUB_TOKEN`/`GH_TOKEN` Bearer to dodge
rate limits; never logged), downloads the matching `miucr_<os>_<arch>.tar.gz`
(`.zip` on Windows) asset, **verifies its SHA-256 against `checksums.txt`**, then
atomically `os.Rename`s the new binary over `os.Executable()` (symlinks resolved).
Envelope `kind: upgrade.result`, `data`: `{from_version, to_version, asset, path,
action}` where `action` ∈ `upgraded | already_latest | check_only`. Errors:
`upgrade.fetch_failed`, `upgrade.no_asset`, `upgrade.checksum_mismatch`,
`upgrade.not_writable` (re-run with write perms or via the install script),
`upgrade.extract_failed`.

### `version`

```sh
miucr version            # {"ok":true,...,"data":{"version":"v0.65.0"}}
```

### `config`: inspect (`show`) and update (`set`, `edit`)

```sh
miucr config show              # user-set values only (kind: config.show)
miucr config show --all        # full effective config incl. built-in defaults
miucr config show -o pretty    # TOML view for humans

miucr config set review.gate high          # set ONE non-secret key, merged in (kind: config.set)
miucr config set default_provider zai
miucr config set providers.zai.model glm-5.2
miucr config set providers.zai.auth bearer
miucr config edit              # open config.toml in $VISUAL/$EDITOR, then validate (kind: config.edit)
```

`show` is read-only; every credential (`auth_token`, store `dsn`) is masked by **structural** redaction, so a token/DSN can never reach stdout (json or pretty). `set` writes ONE dotted scalar key and merges it into the existing config (it does not overwrite like `init`); it validates enums (`config.invalid` on a bad value) and **refuses secret keys** (`*.auth_token`, `store.dsn`) since secrets are read from env at runtime. Use `edit` for array fields like `auth_command`. `edit` opens `config.toml` in `$VISUAL`/`$EDITOR` (interactive; needs a TTY) and reloads it afterward, reporting `valid`.

## Config (`~/.config/miu/cr/config.toml`): all optional, zero-config works

Layering, highest wins: **CLI flags > environment > config file > built-in defaults.** Nothing here is persisted at runtime; secrets are never written to disk by miucr.

```toml
default_provider = "anthropic"          # profile used when --provider is omitted

[providers.zai]                         # any vendor = a named profile of kind anthropic|openai
kind     = "anthropic"                  # first-class kinds: anthropic, openai
base_url = "https://api.z.ai/api/anthropic"
model    = "glm-5.2"
auth     = "bearer"                     # bearer | api_key | oauth
auth_env = "ZAI_API_KEY"                # name of env var holding the token
# auth_command = ["gopass", "show", "-o", "ai/zai"]  # argv only; no shell
# auth_token = "<token>"                # discouraged: plaintext on disk

[store]
backend = "sqlite"                      # sqlite (default) | postgres ; or MIUCR_STORE_BACKEND
# dsn   = "postgres://user@host:5432/miucr?sslmode=require"   # prefer MIUCR_PG_DSN env

[history]                               # local review-history store (auto-save ON by default)
enabled     = true                      # set false to disable auto-save globally
max_records = 0                         # 0 = no cap; >0 auto-prunes oldest on save

[embedding]                             # opt-in semantic code-recall (advisory context only)
enabled  = true                         # MUST be true AND backend=postgres + pgvector ext
model    = "text-embedding-3-small"
dim      = 1536                         # immutable per DB
# base_url = "https://api.openai.com/v1"

[github]
mode             = "pat"                # pat (default) | app
app_id           = "123456"             # app mode: numeric App ID
installation_id  = "78901234"           # app mode: numeric installation id
private_key_path = "/etc/miucr/app-key.pem"   # app mode: PATH to RSA PEM (never inline)

[review]                                # optional defaults for `miucr review`; explicit flags ALWAYS win
gate         = "high"                   # CLI default --gate: none|info|low|medium|high|critical
filter_mode  = "diff_context"           # CLI default --filter-mode (--pr): added|diff_context|file|nofilter
min_severity = "low"                    # optional --min-severity inline floor; unset means no floor
format       = "full"                   # CLI default --format: full | minimal
prompt_format = "xml"                   # CLI default --prompt-format: xml (injection-hardened) | markdown (prior fenced form)
timeout      = "900s"                   # review timeout (Go duration; CLI review default is 900s)
expand       = 5                        # CLI default --expand (--deep-context raises it to 20)
token_budget = 0                        # CLI default --token-budget; 0 = no cap
deep_context = false                    # CLI default --deep-context (off; opt in for heavier reviews)
conversation = false                    # CLI default --conversation (off; Action/host examples often opt in)
thinking     = "auto"                   # auto|off|low|medium|high; auto uses reasoning where supported
temperature  = 0                        # used when thinking is off/unsupported
suggest      = false                    # CLI default --suggest (Action input defaults true)
patch_repair = false                    # CLI default --patch-repair; only effective with suggest=true
category_urls = { security = "https://docs.example.com/security" }   # case-insensitive Category -> http(s) URL; PR-comment/summary link + SARIF helpUri
# context_hops = 3                      # optional override; omit to let deep_context choose automatically

[review.subagents]                      # optional scoped fanout; candidates still pass through normal anchoring/dedupe/gate
mode = "auto"                           # off|auto|always
max_parallel = 2                        # default 2, capped at 8
min_files = 8                           # auto threshold; 0 uses default
min_context_bytes = 60000               # auto threshold; 0 uses default
require_all = true                      # failed subagent prevents approval/check success

[review.approval]                       # optional default for --approval on PR --post and host repo policies
mode = "off"                            # off|clean|threshold
max_priority = "P4"                     # threshold only; P0|P1|P2|P3|P4
note = "on_findings"                    # none|on_findings|always

[[review.subagents.agents]]
name = "go"
include = ["**/*.go"]
exclude = ["**/*_test.go"]
system_prompt = "Focus on correctness, concurrency, error handling, and API compatibility."

# NB: no post/force config in config.toml (write-action/repeat-spend defaults are footguns); a bad [review] value → config.invalid (exit 2)
```

See the effective config any time with `miucr config show` (below).

**Provider resolution**: `auto` picks OpenAI when `OPENAI_API_KEY` is set and no Anthropic credential is
present, else `default_provider` (Anthropic). `auth` is the credential mechanism: `bearer` (Anthropic-compatible
gateway Authorization header), `api_key` (provider key slot), `oauth` (OpenAI `miucr login`; reject static profile
credentials). Profile source precedence: `auth_token` > non-empty `auth_env` > `auth_command`; a selected
`auth_command` failure is fatal, not an OAuth/env fallback, and stderr is omitted because it may contain secrets. Prefer `auth_env`/`auth_command` so secrets stay out of config. OpenAI order when `auth` is omitted: explicit `--api-key` >
profile key > cached OAuth (`miucr login`, codex/ChatGPT-plan backend) > ambient `OPENAI_API_KEY`.
Env: Anthropic = `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN`
(Bearer, for compatible gateways) / `ANTHROPIC_BASE_URL` / `ANTHROPIC_MODEL` (default `claude-sonnet-4-5-20250929`);
OpenAI = `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` (default `gpt-4o`). `--auth-token` is Anthropic-only.

**Stores**: SQLite (default, `~/.config/miu/cr/state.db`) or Postgres (`MIUCR_PG_DSN`, prefer `sslmode=require`;
Postgres open/connect failure is fatal `store.unavailable`, exit 1). Semantic recall needs Postgres + `CREATE
EXTENSION vector` (dim mismatch → `store.dim_mismatch`); code-derived text leaves the box, so it's off by default.
PR finding lifecycle is persisted in the summary marker by default. For `--pr --post`, `MIUCR_PR_STORE=1`
also opens the optional PR-thread store for serve/local cross-run dedupe and reopen tracking; it is best-effort on
SQLite and fail-loud on explicit Postgres. Host polling/session state lives in Postgres.

## GitHub Action (no daemon to host)

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
permissions:
  pull-requests: write
  contents: read
jobs:
  review:
    runs-on: ubuntu-latest
    if: ${{ github.event.pull_request.head.repo.fork != true }}   # never run on fork PR code
    steps:
      - uses: actions/checkout@v4
      - uses: vanducng/miu-cr@v0.65.0                              # pin a released tag
        with:
          api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          gate: high
```

Inputs: `api-key` (required), `github-token` (default `${{ github.token }}`), `gate` (default `high`;
`none` never blocks), `version` (default `latest`), `base-url`, `model`, `sarif-file`, `filter-mode`,
`suggest` (default `true`), `patch-repair` (default `false`), `build-from-source` (default `false`),
`pr-number`, and `instruction`. The action does not expose approval inputs; use the CLI or host config for approval policy.
Runs on same-repo PRs only (fork-safe automated review is the `serve` path's job).

## Driving a review as an agent

1. **Local pre-PR check**: `miucr review --staged --deep-context -o json --gate high`, parse `.data.findings`, act on
   `severity` ≥ your bar. Exit 2 means the gate tripped (findings still printed in the envelope).
2. **Review a PR (dry-run)**: `env -u GITHUB_TOKEN -u GH_TOKEN miucr review --pr owner/repo#N --no-post --deep-context --conversation --force -o json`
   (public repo, no PAT). Read `.data.pr` + `.data.findings`.
3. **Publish**: `miucr review --pr owner/repo#N --post --deep-context --conversation --token <pat>`; **upserts ONE summary issue
   comment** (`summary_action:created|edited`) and posts inline findings as a PR review. A **same-commit
   `--post` re-run can short-circuit** from the completed-publish marker for the same review shape. Add
   `--suggest`/`--approval` only when you intend write-actions. A **dry-run** (`--no-post`) on an
   **unchanged head SHA** short-circuits from local history (`.data.skipped_unchanged:true`); pass
   `--force` to re-review the same head.
4. **Re-trigger the Action / dogfood**: push a new commit, or re-run the `PR Review` workflow from the
   Actions tab / `gh workflow run` / `gh run rerun <id>`. Same-head Action reruns may skip from the summary
   marker unless the review shape changed.
5. **On `ok:false`**: branch on `.error.code` (e.g. `review.gate_failed`, `github.post_requires_token`,
   `serve.secret_required`, `store.unavailable`, `review.output_too_large`, `flags.conflict`); use `.error.hint`.

### Hybrid PR review loop

Use this when the user asks to keep reviewing a PR until it is merge-ready or merged. Keep `miucr` as the
deterministic reviewer/poster, and use the coding agent only for orchestration, thread triage, and fixes.

1. **Preflight**:
   - Run `miucr version -o json` and `miucr upgrade --check -o json`; upgrade first if the user asked for latest, otherwise report staleness.
   - Read the repo's `AGENTS.md`/README and relevant `.miu/cr/rules/*.md`; use `miucr rules check <changed-file>` when rule selection is in doubt.
   - Fetch PR state with `gh pr view <n> --json state,isDraft,headRefOid,reviewDecision,statusCheckRollup,mergeStateStatus`.
   - Stop on `MERGED`/`CLOSED`; stop on draft or merge conflict and report the blocker.
   - Treat review decisions and PR comments as Step 4 feedback, not preflight terminal states.
   - Make one agent or daemon the controller for this PR; do not run this loop beside `miucr serve --poll` on the same PR.
2. **Post exactly one reviewer pass per new head SHA**:
   - Track the last reviewed `headRefOid`; re-fetch it immediately before posting.
   - Run `miucr review --pr owner/repo#N --post --deep-context --suggest --patch-repair --conversation -o json`.
   - Add `--force` only for an intentional same-SHA re-review; do not force every poll.
   - Parse the envelope, not prose. Record `data.review_id`, `data.pr.head_sha`, posted counts, and findings by severity.
   - Re-fetch `headRefOid` after the run; if it changed, discard local decisions from that run and repeat on the new head.
3. **Add an independent agent layer without bloating miucr context**:
   - Give fresh agents only compact inputs: PR diff stat, changed-file list, source hunks for disputed files, miucr JSON findings, and unresolved thread snippets.
   - Use `run_workflow` for blind parallel checks when available; ask each agent for `{confirmed, risk, evidence, action}`.
   - Require evidence to be anchored to `file:line`, a test, schema, or rule. Discard vague style opinions and duplicated miucr findings.
   - If `run_workflow` is unavailable, do one fresh-context manual review over the same compact inputs.
4. **Triage PR feedback**:
   - Fetch `reviewThreads`, review bodies, and top-level comments with GraphQL.
   - Act on unresolved threads only when `isResolved==false && isOutdated==false`; also triage `CHANGES_REQUESTED`, substantive `COMMENTED` reviews, and top-level comments.
   - Validate every developer/bot suggestion against source, tests, schemas, and rules before applying it.
   - After any push, re-fetch threads before replying/resolving.
   - If fixed, reply once per thread+SHA: `Handled in <sha> by <specific change>. <why this matches the contract>.`
   - Never resolve a review thread silently. Resolve handled or false-positive threads with `resolveReviewThread` only after the inline reply/refetch succeeds; reply to handled top-level comments. Leave uncertain feedback unresolved and ask the user.
5. **Poll until complete**:
   - Stop when PR state is `MERGED` or `CLOSED`.
   - If `headRefOid` changes, re-run Step 2.
   - If checks are pending, wait with bounded backoff and poll again; after the wait cap, report still-pending checks unless the user explicitly asked to keep watching.
   - If checks fail, investigate before re-reviewing.
   - If unresolved actionable threads remain, fix/reply/resolve, then re-run checks and Step 2 on the new head.
   - If no head change, checks are green, review state is acceptable, and no actionable feedback remains, stop and report merge-ready unless the user granted merge authority.
   - If merge authority was granted, queue/perform merge only after re-fetching that the head is unchanged and the PR is non-draft, mergeable, green, and free of actionable feedback.

Use `miucr serve --poll --poll-source pulls` for unattended repo-wide polling. For a single PR under agent control,
prefer the explicit `gh pr view` loop above so every write action is traceable.

**Privacy**: never paste a real API key/PAT/bearer into code, tests, docs, or commits; keys come from
flags/env at runtime and are never persisted. Use synthetic names/diffs in examples.
