# Agent hooks

Hooks for coding agents (Claude Code, Codex, Grok, pi), managed in this repo.

## langfuse-trace.py — Langfuse session tracing

Ships **Claude Code** and **Codex** sessions to [Langfuse](https://langfuse.com)
as observation trees: one trace per session, a span per turn, a nested generation
per turn (model + token usage + cost), and a child span per tool call.

```
trace  claude-code: cnb-polaris          session=<session id>  tags=[claude-code, vd-langfuse]
├─ span        turn 1
│  ├─ generation  claude-opus-5   in=10 out=20 cache_read=5
│  ├─ span        tool: Bash
│  └─ span        tool: Read
└─ span        turn 2 …
```

### Why it looks like this

Langfuse's OTLP endpoint ingests **traces only** — Claude Code's built-in
OpenTelemetry export emits **metrics and logs**, so pointing `OTEL_*` at Langfuse
does not produce sessions. Tracing therefore reads each agent's own session
transcript and synthesizes spans, which is also what gets tool calls and
per-turn token usage into the trace.

Transport is **OTLP over HTTP/JSON built with stdlib `urllib`** — no `langfuse`
SDK, no `uv`, no `pip`, matching the rest of these hooks.

### Setup

1. Put your Langfuse keys in the environment or `~/.envrc`:
   ```sh
   export LANGFUSE_PUBLIC_KEY=pk-lf-…
   export LANGFUSE_SECRET_KEY=sk-lf-…
   export LANGFUSE_BASE_URL=https://cloud.langfuse.com   # or https://us.cloud.langfuse.com
   ```
   Hooks don't inherit a direnv-loaded shell, so the exporter falls back to
   reading **literal** `LANGFUSE_*` assignments out of `~/.envrc`. It never
   executes that file — a real `.envrc` shells out to secret managers, which
   would hang a hook. Values using `$(…)` are skipped.

2. Install hooks for Claude Code + Codex:
   ```sh
   vd install hooks
   ```
   Registers `Stop` + `SessionEnd` (Claude Code) and `Stop` (Codex, via
   `~/.codex/hooks.json` — your `notify` chain is left alone).

3. pi is traced by the official [`pi-langfuse`](https://langfuse.com/integrations/developer-tools/pi-agent)
   extension instead (`pi install npm:pi-langfuse`, registered in the dotfiles-managed
   `~/.pi/agent/settings.json`). It traces in-process — richer than this exporter
   (per-request generations, tool observations, scores, secret redaction) — and
   reads the same `LANGFUSE_*` environment variables. The exporter keeps its
   `--agent pi` adapter for one-off backfills of old sessions only.

### Usage outside hooks

```sh
langfuse-trace.py --agent codex --latest        # export the newest Codex session
langfuse-trace.py --agent pi --scan --limit 50  # backfill recent pi sessions
langfuse-trace.py --transcript <file> --json    # explicit file, machine-readable result
langfuse-trace.py --agent claude-code --latest --force   # re-send turns already shipped
```

### Notes

- **Incremental and idempotent.** A state file (`$XDG_STATE_HOME/vd/langfuse-turns.json`)
  records how many turns of each session have shipped, so firing on every turn
  never duplicates. Span ids are derived from the session id, so later turns
  append to the same trace. `VD_LANGFUSE_TRACE_SEED` starts a fresh trace.
- **Fail-open.** The exporter always exits 0 and is silent without credentials —
  observability must never block or slow an agent turn. Set `VD_LANGFUSE_DEBUG=1`
  to see what it did.
- **Bounded per fire.** Each invocation ships at most `--max-turns` turns
  (default 25, `VD_LANGFUSE_MAX_TURNS` to change, `0` for unlimited) and the
  rest is picked up on later turns. Without the cap, the first fire against a
  long existing session ships thousands of spans while a synchronous `Stop`
  hook blocks the turn — a 2,200-span backfill measured ~10 min against
  Langfuse Cloud. Spans are also batched 400/request so a large deliberate
  backfill (`--scan`, or `--max-turns 0`) can't blow the request limit.
- **Cost:** pi reports real per-message cost and it's sent verbatim. Claude Code
  and Codex don't, so Langfuse prices them from its own model table — define
  prices in Langfuse for any model it doesn't know (e.g. `gpt-5.6-sol`), or its
  default rate will produce inflated numbers.
- Tuning: `VD_LANGFUSE_MAX_CHARS` (truncation, default 20000),
  `VD_LANGFUSE_USER_ID`, `VD_LANGFUSE_ENVIRONMENT`, `VD_LANGFUSE_STATE`,
  `VD_LANGFUSE_ENVRC`.
- Tests: `python3 hooks/test_langfuse.py` — fully offline (a local HTTP server
  stands in for Langfuse).

## agent-notify.py — Telegram notifier

Pings a Telegram chat when **Claude Code**, **Codex**, or **Grok** finishes a
turn or needs approval, with what / when / where context for quick triage. Each
agent has a distinct colour — **🟠 Claude**, **🔵 Codex**, **⚫ Grok** — and the
message preview is an expandable blockquote (tap to expand) so long turns stay
tidy.

```
🟠 CLAUDE · ✅ turn complete          🔵 CODEX · 🔔 needs approval
🕒 14:42 · Mon 15 Jun  💻 host         🕒 …  💻 host
📂 vd-cli                             📂 cnb-polaris
📁 ~/git/personal/agents/vd-cli       📁 ~/git/work/cnb/products/cnb-polaris
🖥 vendor:vdcli:0  (session:window:pane) 🖥 cnb:astro:2
❝ expandable preview of the last     ❝ expandable preview… ❞
  assistant message… ❞
```

Status icons: ✅ turn complete · 🔔 needs you / needs approval.

### Setup (any machine)

1. Export the bot token + chat id in your environment — e.g. `~/.envrc` (direnv):
   ```sh
   export TELEGRAM_BOT_TOKEN=123456:xxxx
   export TELEGRAM_CHAT_ID=000000000          # DM the bot, then GET /getUpdates; comma-separate for several chats
   # optional — chain a previously-configured Codex notify program:
   export CODEX_NOTIFY_FORWARD="/path/to/old-notify"
   export CODEX_NOTIFY_FORWARD_ARG="turn-ended"
   ```
   The script reads the live env and falls back to parsing `~/.envrc`, so it
   works even when the agent process wasn't launched with direnv loaded.

2. Wire both agents (idempotent, backs up configs):
   ```sh
   python3 ~/skills/hooks/install.py
   ```

That registers:
- **Claude** `~/.claude/settings.json` — `Stop` + `Notification` hooks → `agent-notify.py claude …` (JSON on stdin).
- **Codex** `~/.codex/config.toml` — `notify = ["python3", ".../agent-notify.py", "codex"]` (JSON as last arg). Any prior `notify` is preserved if you set `CODEX_NOTIFY_FORWARD`.
- **Grok** is wired from the dotfiles stow package (`make stow-grok`) via `~/.grok/hooks/lifecycle.json` → `agent-notify.py grok …` (JSON on stdin).

### Notes

- **Stdlib only** — no `pip`, no `jq`, no Node. Secrets never live in this repo (env only).
- Claude `Stop` (turn-complete) pushes are **suppressed by default** to avoid per-turn spam during autonomous / auto-accept runs — the "your turn" ping comes from the idle `Notification` event instead. Set `AGENT_NOTIFY_STOP=always` to restore the legacy ping on every turn. `AGENT_NOTIFY_DRYRUN=1` prints the message text instead of sending.
- Uninstall: remove the two entries from `settings.json`, restore `config.toml` from its `.bak.*`, and unset the env vars.

## get the chat id

```sh
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates" \
  | python3 -c "import sys,json;print({(u.get('message') or {}).get('chat',{}).get('id') for u in json.load(sys.stdin)['result']})"
```
(DM the bot once first so it appears in updates.)
