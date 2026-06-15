# Agent hooks

Hooks for coding agents (Claude Code, Codex), managed in this repo.

## agent-notify.py — Telegram notifier

Pings a Telegram chat when **Claude Code** or **Codex** finishes a turn or needs
approval, with what / when / where context for quick triage.

```
✳️ CLAUDE · ✅ turn complete        🟢 CODEX · 🔔 needs approval
🕒 10:56 · Mon 15 Jun  💻 host       🕒 …  💻 host
📂 vd-cli                            📂 skills
📁 ~/git/personal/agents/vd-cli      📁 ~/skills
🖥 main:vdcli   (tmux session:win)   💬 Run: rm -rf build/ ?
💬 Claude needs permission to run Bash
```

### Setup (any machine)

1. Export the bot token + chat id in your environment — e.g. `~/.envrc` (direnv):
   ```sh
   export TELEGRAM_BOT_TOKEN=123456:xxxx
   export TELEGRAM_CHAT_ID=000000000          # DM the bot, then GET /getUpdates
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

### Notes

- **Stdlib only** — no `pip`, no `jq`, no Node. Secrets never live in this repo (env only).
- Claude `Stop` fires on **every** turn — expect a ping per completed response.
- Uninstall: remove the two entries from `settings.json`, restore `config.toml` from its `.bak.*`, and unset the env vars.

## get the chat id

```sh
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates" \
  | python3 -c "import sys,json;print({(u.get('message') or {}).get('chat',{}).get('id') for u in json.load(sys.stdin)['result']})"
```
(DM the bot once first so it appears in updates.)
