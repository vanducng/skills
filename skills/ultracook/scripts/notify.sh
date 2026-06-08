#!/usr/bin/env bash
# notify.sh — push-notification wrapper. Tries terminal-notifier → ntfy.sh →
# Slack webhook → log fallback. Always exits 0 on bad-args=2; never breaks
# the caller.
#
# Used by ultracook on terminal=blocked (semi/auto modes) so the user gets paged
# when a goal stops mid-flight. Cross-runtime: works on both Claude Code (as
# fallback when out-of-session) and Codex.
#
# Usage:
#   notify.sh --title "<t>" --body "<b>" [--deep-link <url>]
#
# Tool requirements (any one):
#   - terminal-notifier (macOS):  brew install terminal-notifier
#   - ntfy (any OS):              brew install ntfy + set NTFY_TOPIC env
#   - Slack webhook:              set SLACK_WEBHOOK_URL env (treat as secret)
#   - fallback log:               always available; writes to ~/.ultracook/notifications.log

set -uo pipefail

TITLE=""; BODY=""; DEEP_LINK=""
while [ $# -gt 0 ]; do
  case "$1" in
    --title)     TITLE="${2:-}"; shift 2 ;;
    --body)      BODY="${2:-}"; shift 2 ;;
    --deep-link) DEEP_LINK="${2:-}"; shift 2 ;;
    --help|-h)   echo "usage: notify.sh --title <t> --body <b> [--deep-link <url>]"; exit 0 ;;
    *) echo "notify.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -z "$TITLE" ] && { echo "notify.sh: --title required" >&2; exit 2; }
[ -z "$BODY" ]  && { echo "notify.sh: --body required" >&2; exit 2; }

# Try notification backends in order. Each prints "sent via X" and exits 0
# on success.

# 1. terminal-notifier (macOS)
if command -v terminal-notifier >/dev/null 2>&1; then
  if [ -n "$DEEP_LINK" ]; then
    terminal-notifier -title "$TITLE" -message "$BODY" -open "$DEEP_LINK" >/dev/null 2>&1
  else
    terminal-notifier -title "$TITLE" -message "$BODY" >/dev/null 2>&1
  fi
  echo "sent via terminal-notifier"
  exit 0
fi

# 2. ntfy (cross-platform; requires NTFY_TOPIC env)
if command -v ntfy >/dev/null 2>&1 && [ -n "${NTFY_TOPIC:-}" ]; then
  ntfy publish "$NTFY_TOPIC" --title "$TITLE" "$BODY" >/dev/null 2>&1
  echo "sent via ntfy ($NTFY_TOPIC)"
  exit 0
fi

# 3. Slack webhook (treat URL as secret; never log it)
if [ -n "${SLACK_WEBHOOK_URL:-}" ] && command -v curl >/dev/null 2>&1; then
  payload=$(printf '{"text":"*%s*\\n%s"}' "${TITLE//\"/\\\"}" "${BODY//\"/\\\"}")
  if curl -sf -X POST -H 'Content-Type: application/json' -d "$payload" "$SLACK_WEBHOOK_URL" >/dev/null 2>&1; then
    echo "sent via Slack webhook"
    exit 0
  fi
fi

# 4. Log fallback — always works.
LOG="$HOME/.ultracook/notifications.log"
mkdir -p "$(dirname "$LOG")"
printf '%s [%s] %s%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$TITLE" "$BODY" \
  "${DEEP_LINK:+ ($DEEP_LINK)}" >> "$LOG"
echo "logged to $LOG (no notification backend available)"
echo "  install with: brew install terminal-notifier  (macOS)"
echo "                brew install ntfy + set NTFY_TOPIC env"
echo "                set SLACK_WEBHOOK_URL env"
exit 0
