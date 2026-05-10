#!/usr/bin/env bash
# probe-context-pct.sh — feature-detect context utilization probe.
#
# Sources, in priority order:
#   1. Statusline payload via STATUSLINE_JSON env var (if hook-injected)
#   2. tiktoken estimate over current transcript (if available)
#   3. Unknown — caller should skip phase-restart and rely on native auto-compact
#
# Usage: probe-context-pct.sh
# Stdout: JSON `{"pct": <int>, "source": "statusline|tiktoken|unknown"}`

set -uo pipefail

if [[ -n "${STATUSLINE_JSON:-}" ]]; then
  pct=$(printf '%s' "$STATUSLINE_JSON" | jq -r '.context_used_pct // empty' 2>/dev/null || true)
  if [[ -n "$pct" ]]; then
    jq -nc --argjson p "$pct" '{pct: $p, source: "statusline"}'
    exit 0
  fi
fi

PYTHON_BIN="${PYTHON_BIN:-$HOME/.claude/skills/.venv/bin/python3}"
[[ ! -x "$PYTHON_BIN" ]] && PYTHON_BIN="$(command -v python3 || true)"

if [[ -x "$PYTHON_BIN" ]] && "$PYTHON_BIN" -c "import tiktoken" >/dev/null 2>&1; then
  # Use VD_AUTOLOOP_TRANSCRIPT (path) if hook supplies one; else best-effort
  if [[ -n "${VD_AUTOLOOP_TRANSCRIPT:-}" && -f "$VD_AUTOLOOP_TRANSCRIPT" ]]; then
    pct=$("$PYTHON_BIN" - <<PY 2>/dev/null
import os, sys, tiktoken
path = os.environ["VD_AUTOLOOP_TRANSCRIPT"]
with open(path) as f:
    text = f.read()
enc = tiktoken.get_encoding("cl100k_base")
tokens = len(enc.encode(text))
window = int(os.environ.get("VD_AUTOLOOP_CONTEXT_WINDOW", "200000"))
print(min(99, int(tokens * 100 / window)))
PY
)
    if [[ -n "$pct" ]]; then
      jq -nc --argjson p "$pct" '{pct: $p, source: "tiktoken"}'
      exit 0
    fi
  fi
fi

jq -nc '{pct: -1, source: "unknown"}'
exit 0
