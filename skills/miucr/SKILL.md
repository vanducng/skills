---
name: miucr
description: Review code/diffs/PRs with the owned `miucr` CLI (miu-cr, a pure-Go AI code reviewer). Use when asked to review staged changes, a commit, a ref range, or a GitHub PR; to run/parse a gated review; to drive reviews over MCP; or to run the serve webhook/poll daemon or GitHub Action. Output is the stable `miucr.cli/v1` JSON envelope — parse it, don't grep prose.
---

# miucr — owned AI code-review CLI (v0.11.0)

`miucr` (the **miu-cr** project) is a fast, **pure-Go** (`CGO_ENABLED=0`) AI code reviewer.
It keeps the correctness-critical parts **deterministic** (file selection, context assembly,
line-anchoring, severity gating, dedupe) and uses the LLM only for judgment (finding bugs,
proposing fixes). It runs four ways:

- **Local review** — `miucr review` over a staged diff, a commit, or a ref range.
- **GitHub PR review** — `miucr review --pr` (dry-run by default; `--post` publishes inline + summary comments).
- **serve daemon** — HMAC webhook (default) and/or opt-in poll trigger; optional REST API + GitHub App auth.
- **MCP server** — `miucr mcp` exposes `review_run` / `review_get` over stdio to any agent host.

## Output contract — `miucr.cli/v1` envelope (parse this)

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

`kind` per command: `version`, `review.result`, `rules.check`, `rules.init`, `init.result`, `login.result`,
`history.list`, `history.record`, `history.prune`, `error`
(REST: `review.accepted` / `review.result`). **Secrets never appear** in the envelope, logs, or on disk
(credential-named fields are scrubbed; finding `rationale`/`suggested_patch` prose is exempt).

### Exit codes (gate → exit mapping)

| Exit | Meaning |
| ---- | ------- |
| `0`  | Success — no finding reached `--gate`. |
| `1`  | Operational error — missing credentials, internal failure, store unavailable. |
| `2`  | **Gate failed** (a finding's severity ≥ `--gate`) **or** invalid invocation (bad gate, conflicting/zero modes, bad `--output`). |

Severities low→high: `info` < `low` < `medium` < `high` < `critical`. A `review.gate_failed`
error is emitted *after* the normal `review.result` envelope (the findings still print), then exit 2.

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/vanducng/miu-cr/main/install.sh | sh   # asset-aware latest
curl -fsSL https://raw.githubusercontent.com/vanducng/miu-cr/main/install.sh | sh -s -- v0.11.0   # pin
brew install vanducng/tap/miucr                                                     # Homebrew
go install github.com/vanducng/miu-cr/cmd/miucr@latest                              # Go 1.25+
```

Verify: `miucr version` → `{"ok":true,...,"data":{"version":"v0.11.0"}}`.
Config (optional) at `~/.config/miu/cr/config.toml`; state DB at `~/.config/miu/cr/state.db`.
Repo rules at `.miu/cr/rules/*.md` — **never a flat `.miucr/`**.

## Onboarding (`miucr init`)

`miucr init` is the fastest path to a working config. It walks a clean, sectioned
wizard — **provider → provider-aware auth → project rules** — then writes
`~/.config/miu/cr/config.toml` (dir `0700`, file `0600`, **deltas only** — the
chosen provider block, never the full built-in defaults) and ends on the literal
`miucr review --staged`.

```sh
miucr init                                  # interactive wizard (idempotent: Overwrite? y/N)
miucr init --non-interactive --provider anthropic --auth-env ANTHROPIC_API_KEY --yes
```

- **Provider-aware auth menu**: `openai` offers **browser login (OAuth, default)**
  — review on your ChatGPT/Codex plan, no API key — plus env-var or paste; it runs
  the same PKCE loopback flow as `miucr login` and caches the token in `oauth.json`
  (config records just `default_provider = "openai"`, no secret). `anthropic` offers
  env-var (default) or paste — **no OAuth** (Anthropic ToS). `custom` asks kind +
  base URL, then env-var or paste.
- **Default writes no secret** — only the env-var **name** (`auth_env`). A literal
  `auth_token` lands only on explicit paste + confirm (after a plaintext-on-disk warning).
- Flags: `--provider anthropic|openai|custom`, `--auth oauth|env|paste` (non-interactive
  selector), `--auth-env <NAME>`, `--base-url <gateway>`, `--no-rules`, `--force`,
  `--yes`, `--non-interactive`. `--auth oauth` is interactive-only (needs a browser) —
  non-interactive errors `init.aborted` toward `miucr login`. Envelope `kind: init.result`
  (`data.auth_method` = `oauth|env|paste`, `data.next` = `miucr review --staged`); errors
  `init.aborted` / `config.write_failed`.
- `init` is **optional** — zero-config still works when a provider key is on the env.
  With no config **and** no key, `review` prints a soft one-line nudge to run `init`.

## Examples (copy-paste starters)

The repo ships an [`examples/`](https://github.com/vanducng/miu-cr/tree/main/examples)
tree: `rules/{go-api,typescript-node,python-data}.md`,
`github-action/code-review.yml` (fork-safe `pull_request_target`),
`mcp-setup/{claude-code,cursor,codex}` + `README-mcp.md`, and
`docker/{Dockerfile,docker-compose.yml}` (pure-Go `CGO_ENABLED=0` distroless image
for `miucr serve`). Onboarding walkthrough lives at the docs
[Getting started](https://miucr.vanducng.dev/onboarding/) page.

## Commands & exact flags

Global flags (all commands): `-o, --output json|pretty|sarif` (default `json`), `--timeout <dur>`
(default `30s`; `review` auto-bumps to `300s` unless `--timeout` is set explicitly).
`sarif` is **review-only**: it emits a SARIF 2.1.0 document (NOT the envelope) for
code-scanning/IDEs — `ruleId`=category, `level` from severity, repo-relative paths;
upload it with `github/codeql-action/upload-sarif`. `pretty` is a local reporter
(jumpable `file:line`, excerpt, patch; color on a TTY). `review --pr` also takes
`--filter-mode added|diff_context|file|nofilter` (default `diff_context`) controlling
which findings are inline-eligible; `file`/`nofilter` route off-diff findings to the
summary/SARIF/local output, never inline.

### `review` — needs **exactly one** mode

```sh
miucr review --staged                     # staged changes vs the index
miucr review --from main --to HEAD        # ref range (--from and --to required together)
miucr review --commit HEAD~1              # one commit vs its parent
miucr review --pr owner/repo#123          # a GitHub PR (dry-run by default)
```

| Flag | Default | Notes |
| ---- | ------- | ----- |
| `--staged` | off | Review the **index** (what you're about to commit), not HEAD. |
| `--from` / `--to` | — | Range mode; **required together**. |
| `--commit <ref>` | — | Single commit vs first parent. |
| `--pr <url\|owner/repo#N>` | — | GitHub PR; `https://github.com/owner/repo/pull/N` or `owner/repo#N`. |
| `--gate none\|info\|low\|medium\|high\|critical` | `high` | Exit 2 when a finding reaches this severity. `none` never fails. |
| `--repo <dir>` | `.` | Repository directory. |
| `--include` / `--exclude` | — | Repeatable doublestar globs (path must match / drop). |
| `--ext go,ts,...` | — | Restrict to these file extensions. |
| `--expand <n>` | `5` | Context lines above/below each hunk (`0` disables). |
| `--token-budget <n>` | `0` | Approx token budget; over budget degrades context (`0` disables). |
| `--provider anthropic\|openai\|<name>\|auto` | `auto` | LLM profile. |
| `--api-key` / `--base-url` / `--auth-token` / `--model` | — | Provider overrides; **never persisted**. |
| `--token <pat>` | — | GitHub PAT (overrides `GITHUB_TOKEN`/`GH_TOKEN`); required only for `--post`; never persisted. |
| `--post` / `--no-post` | `--no-post` (for `--pr`) | Publish vs dry-run; mutually exclusive (`flags.conflict`). |
| `--suggest` | OFF | Native one-click suggestions for proven single-line replacements; requires `--post`; author-applied, never pushed. |
| `--approve-clean` | OFF | Submit `Event=APPROVE` only on a clean, non-fork, trusted-author PR; else degrades to COMMENT (never errors); requires `--post`. |
| `--filter-mode added\|diff_context\|file\|nofilter` | `diff_context` | Inline-eligibility filter on `--pr`. `file`/`nofilter` route off-diff findings to summary/SARIF/local, never inline (GitHub 422s an off-diff comment). |
| `--mode review\|checks` | `review` | GitHub reporter on `--pr --post`. `review` posts inline comments + a summary. `checks` posts a GitHub CheckRun with annotations (survives force-push, works on fork PRs, can be a **required** check); conclusion maps from the gate (gate-clean→`success`, gate-hit→`failure`); needs `checks: write`. |
| `--sarif-out <path>` | — | Also write a SARIF 2.1.0 report to `<path>` from the SAME single review run (in addition to `--output`/posting). Written only on success (atomic temp+rename); a failed run leaves no file. This is how the Action does single-pass SARIF — no second LLM call. |
| `--no-save` | off | Skip persisting this run to the local history store (every review is saved by default). |
| `--force` | off | On `--pr`, re-review even when the head SHA is unchanged since the last saved review. By default an unchanged head SHA short-circuits (`skipped_unchanged`, no LLM pass); a new commit always re-reviews. |
| `-v, --verbose` / `-q, --quiet` | auto | Progress to **stderr** (stdout envelope unchanged). Auto-on when stderr is a TTY; `-v` forces on, `-q` forces off; mutually exclusive. Piped/CI stays silent. |

**`review.result` data** (local and `--pr`):

```jsonc
"data": {
  "findings": [
    { "file": "internal/foo/bar.go", "line": 42, "end_line": 42,
      "severity": "high", "category": "bug",
      "rationale": "…why this is a problem…",
      "suggested_patch": "…optional minimal fix…",
      "quoted_code": "…verbatim source the finding anchors to…" }
  ],
  "stats": { "files_changed": 3, "files_reviewed": 2, "findings_total": 2,
             "findings_dropped": 1, "max_severity": "high", "gate": "high",
             "truncation_level": "full",            // full | hunks_only | filenames_only
             "rules_applied": 5, "rules_truncated": false },
  "review_id": "rev_...",  // additive: the saved history record id ("" with --no-save)
  // additive, only on --pr when an unchanged head SHA short-circuited (no LLM pass);
  // both omitted on a normal review:
  "skipped_unchanged": true, "prior_review_id": "rev_prior",
  "pr": {  // only on --pr
    "owner": "owner", "repo": "repo", "number": 123, "head_sha": "deadbeef",
    "is_fork": false, "posted": false, "posted_inline": 0, "summary_action": "none",
    "approve_action": "commented", "approve_reason": "not_requested", "suggestions_posted": 0,
    // additive, omitted when empty:
    "mode": "review",                 // review (default) | checks
    "check_run_id": 0, "check_conclusion": "",  // --mode checks only (success|failure)
    "fallback_annotations": 0 }       // >0 when a fork-PR 403 under Actions fell back to ::error:: workflow annotations (review did NOT hard-fail); summary_action then "fork_fallback"
}
```

`findings_dropped` = findings rejected by line-anchor drift (their quote no longer matches the reviewed
revision — kills position drift). `summary_action` is `created|edited|none`; re-runs are idempotent
(sentinel `<!-- miu-cr-review -->` summary + per-comment `<!-- miucr:fp=... -->` line-free fingerprints).
A public-PR dry-run needs **no GitHub PAT** (LLM key still required); `--post` and private repos need a PAT with `repo` scope.

### `serve` — webhook daemon (default) + opt-in poll

```sh
WEBHOOK_SECRET=… GITHUB_TOKEN=… ANTHROPIC_API_KEY=… \
  miucr serve --addr :8080 --repos owner/repo,owner/other --gate high
```

| Flag | Default | Notes |
| ---- | ------- | ----- |
| `--addr` | `:8080` | Webhook listen address. |
| `--gate` | `high` | **Publish-severity only** — which findings get posted; never affects liveness/exit. |
| `--repos` | — | **Required** owner/repo allowlist (comma-separated); other repos are ignored. |
| `--poll` | off | Opt-in trigger: periodically ask GitHub which PRs need review. Webhook stays default. |
| `--poll-interval` | `1m0s` | Floor; effective = `max(this, X-Poll-Interval)`. |
| `--poll-source notifications\|pulls` | `notifications` | Candidate source. `pulls` = full coverage / cold-start-complete. |

Env: `WEBHOOK_SECRET` (required unless poll-only), `GITHUB_TOKEN`/`GH_TOKEN` (required unless `[github] mode=app`),
`ANTHROPIC_API_KEY` (or compatible). Endpoints: `POST /webhook` (HMAC), `GET /healthz`. Each new head SHA = one full
LLM review; allowlist + per-head dedup are the only spend guards. serve inherits `--suggest`/`--approve-clean` **OFF**.

**Opt-in REST API** — set `MIUCR_API_TOKEN` (env-only, no flag) to register `/v1`:

```sh
MIUCR_API_TOKEN=$(openssl rand -hex 32) WEBHOOK_SECRET=… GITHUB_TOKEN=… ANTHROPIC_API_KEY=… \
  miucr serve --addr :8080 --repos owner/repo
# Queue (202 + server-generated crypto/rand id):
curl -sS -X POST https://host/v1/reviews -H "Authorization: Bearer $MIUCR_API_TOKEN" \
  -H 'Content-Type: application/json' -d '{"owner":"acme","repo":"widgets","number":42}'
# Read back (whitelist: id,status,created_at,findings,stats — never the clone path):
curl -sS https://host/v1/reviews/<id> -H "Authorization: Bearer $MIUCR_API_TOKEN"
```

Status lifecycle: `pending` → `done`/`failed`. HTTP map: `400` bad body, `401` missing/wrong bearer
(empty token can never auth), `403` off-allowlist, `404` unknown id, `405` wrong method, `413` body > 64 KB.
**Single-operator**: one shared bearer = one trust boundary (not multi-tenant).

**GitHub App auth** (opt-in alternative to PAT) — `[github] mode=app` in config (see below).

### `rules` — project review context

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

### `history` — browse saved reviews

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

### `mcp` — review engine over stdio

```sh
miucr mcp                       # stdio transport (default)
miucr mcp --transport stdio
```

Reviews the repo in the **current working directory** — launch from (or point the host at) the target repo.
Stdout carries only MCP frames; logs/errors go to stderr. Tool outputs are byte-bounded (1 MiB) → oversized
fails `review.output_too_large` (narrow the review).

- **`review_run`** — args `{ staged, from, to, commit, gate, expand, token_budget }` (exactly one mode, same
  validation as the CLI). Returns `{ id, findings, stats }`; `id` is the persisted review id.
- **`review_get`** — args `{ id }`. Returns `{ id, repo_dir, mode, head_sha, created_at, findings, stats }`.

Register in Claude Code: `claude mcp add --transport stdio miucr -- miucr mcp --transport stdio`
(provide a provider key via the host's `env`, e.g. `ANTHROPIC_API_KEY`).

### `login` — OAuth to review on your ChatGPT plan

```sh
miucr login --provider openai     # PKCE loopback OAuth; caches token at ~/.config/miu/cr/oauth.json (0600)
miucr login --no-browser          # headless/SSH: print the authorize URL instead of opening a browser
```

Reviews authed by this token route to the **codex backend** (`chatgpt.com/backend-api/codex`,
Responses protocol) so they run on the user's **ChatGPT Pro/Max subscription**, not a billed key.
On this path the model defaults to `gpt-5.5` (the codex backend rejects api.openai.com models like
`gpt-4o`); `miucr init` writes `model = "gpt-5.5"` into `[providers.openai]` so it is visible + editable.
Precedence: `--model` > `MIUCR_CODEX_MODEL` > the config `model` (if not `gpt-4o`) > `gpt-5.5`.
`--provider` is an explicit flag backed by a registry — `openai` is the only entry
(`--provider anthropic`/unknown → `login.provider_unsupported`; Anthropic OAuth is ToS-prohibited).
Loopback binds an allow-listed port (`1455`, then `1457`). Envelope `kind: init.result`-style
**secret-free** payload: `{provider, oauth_path, expires_at, account_id, has_api_key}` — **no tokens**.
Errors: `login.provider_unsupported`, `login.port_unavailable`, `login.timeout`, `login.exchange_failed`, `login.write_failed`.

**Precedence**: the cached OAuth credential sits **below** an explicit `--api-key` / `OPENAI_API_KEY`
in OpenAI resolution — an explicit key always wins; OAuth is consulted only when no OpenAI key is set.
`oauth.json` is gitignored, `0600`, never logged/in-envelope. No `miucr logout` (delete the file by hand).
**CI uses an `OPENAI_API_KEY` secret, not OAuth** (browser-interactive) — `miucr review --provider openai`.

### `upgrade` (alias `update`) — self-update from GitHub Releases

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
miucr version            # {"ok":true,...,"data":{"version":"v0.11.0"}}
```

## Config (`~/.config/miu/cr/config.toml`) — all optional, zero-config works

Layering, highest wins: **CLI flags > environment > config file > built-in defaults.** Nothing here is persisted at runtime; secrets are never written to disk by miucr.

```toml
default_provider = "anthropic"          # profile used when --provider is omitted

[providers.zai]                         # any vendor = a named profile of kind anthropic|openai
kind     = "anthropic"                  # first-class kinds: anthropic, openai
base_url = "https://api.z.ai/api/anthropic"
model    = "glm-5.2"
auth_env = "ZAI_API_KEY"                # RECOMMENDED: name of env var holding the token
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

[review]                                # render a finding's Category as a docs link (TRUSTED config only)
category_urls = { security = "https://docs.example.com/security" }   # case-insensitive key -> http(s) URL; sets PR-comment/summary link + SARIF helpUri
```

**Provider resolution** — `auto` picks OpenAI when `OPENAI_API_KEY` is set and no Anthropic credential is
present, else `default_provider` (Anthropic). OpenAI order: explicit `--api-key` > `OPENAI_API_KEY` > profile key >
a cached `miucr login` OAuth token (routes to the codex/ChatGPT-plan backend) — an explicit key always wins.
Env: Anthropic = `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN`
(Bearer, for compatible gateways) / `ANTHROPIC_BASE_URL` / `ANTHROPIC_MODEL` (default `claude-sonnet-4-5-20250929`);
OpenAI = `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` (default `gpt-4o`). `--auth-token` is Anthropic-only.

**Stores**: SQLite (default, `~/.config/miu/cr/state.db`) or Postgres (`MIUCR_PG_DSN`, prefer `sslmode=require`;
Postgres open/connect failure is fatal `store.unavailable`, exit 1). Semantic recall needs Postgres + `CREATE
EXTENSION vector` (dim mismatch → `store.dim_mismatch`); code-derived text leaves the box, so it's off by default.
Opt-in PR-thread resolution store via `MIUCR_PR_STORE` (serve/local; nil on the Action path).

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
      - uses: vanducng/miu-cr@v0.11.0                              # pin a released tag
        with:
          api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          gate: high
```

Inputs: `api-key` (required), `github-token` (default `${{ github.token }}`), `gate` (default `high`;
`none` never blocks), `version` (default `latest`), `base-url`, `model`. Comment-only (no `--suggest`/`--approve-clean`).
Runs on same-repo PRs only (fork-safe automated review is the `serve` path's job).

## Driving a review as an agent

1. **Local pre-PR check** — `miucr review --staged -o json --gate high`, parse `.data.findings`, act on
   `severity` ≥ your bar. Exit 2 means the gate tripped (findings still printed in the envelope).
2. **Review a PR (dry-run)** — `env -u GITHUB_TOKEN -u GH_TOKEN miucr review --pr owner/repo#N --no-post -o json`
   (public repo, no PAT). Read `.data.pr` + `.data.findings`.
3. **Publish** — `miucr review --pr owner/repo#N --post --token <pat>`; idempotent re-runs (`posted_inline:0`,
   `summary_action:edited`). Add `--suggest`/`--approve-clean` only when you intend write-actions. A re-review on
   an **unchanged head SHA** short-circuits (`.data.skipped_unchanged:true`, no LLM pass); pass `--force` to override.
4. **Re-trigger the Action / dogfood** — push a new commit, or re-run the `PR Review` workflow from the
   Actions tab / `gh workflow run` / `gh run rerun <id>`. Each new head SHA is a fresh review.
5. **On `ok:false`** — branch on `.error.code` (e.g. `review.gate_failed`, `github.post_requires_token`,
   `serve.secret_required`, `store.unavailable`, `review.output_too_large`, `flags.conflict`); use `.error.hint`.

**Privacy**: never paste a real API key/PAT/bearer into code, tests, docs, or commits; keys come from
flags/env at runtime and are never persisted. Use synthetic names/diffs in examples.
