#!/usr/bin/env bash
# detect-runtime.sh — identify which agent runtime is invoking pursue.
#
# Stdout: "claude-code" | "codex"
# Stderr + exit 2: "ambiguous" when both runtime signals are present
# Stderr + exit 3: "unknown" when no signal is found
#
# Detection precedence (top → bottom):
#   1. $PURSUE_RUNTIME override (claude-code | codex)
#   2. Both Claude AND Codex env vars set → ambiguous (fail closed)
#   3. CLAUDE_PROJECT_DIR or CLAUDE_TOOL_USE_ID set → claude-code
#   4. CODEX_SESSION_ID set → codex
#   5. Codex session recency-fallback (when env propagation broken in subshells):
#      a Codex session JSONL modified within last 5 min + codex on PATH → codex
#   6. codex on PATH AND claude NOT on PATH → codex
#   7. claude on PATH → claude-code
#   8. else → unknown

set -o pipefail

# 1. Explicit override
case "${PURSUE_RUNTIME:-}" in
  claude-code|codex) echo "$PURSUE_RUNTIME"; exit 0 ;;
esac

CLAUDE_SIGNAL=""
CODEX_SIGNAL=""
[ -n "${CLAUDE_PROJECT_DIR:-}" ] || [ -n "${CLAUDE_TOOL_USE_ID:-}" ] && CLAUDE_SIGNAL="yes"
[ -n "${CODEX_SESSION_ID:-}" ] && CODEX_SIGNAL="yes"

# 2. Ambiguous (fail closed)
if [ -n "$CLAUDE_SIGNAL" ] && [ -n "$CODEX_SIGNAL" ]; then
  echo "detect-runtime.sh: ambiguous — both CLAUDE_* and CODEX_SESSION_ID set. Set PURSUE_RUNTIME explicitly." >&2
  exit 2
fi

# 3. Claude Code env signal
if [ -n "$CLAUDE_SIGNAL" ]; then echo "claude-code"; exit 0; fi
# 4. Codex env signal
if [ -n "$CODEX_SIGNAL" ]; then echo "codex"; exit 0; fi

# 5. Codex recency fallback — for subshells where CODEX_SESSION_ID doesn't propagate.
# A Codex JSONL modified within last 5 min suggests an active Codex session.
if command -v codex >/dev/null 2>&1; then
  recent=$(find "$HOME/.codex/sessions" -maxdepth 2 -name '*.jsonl' -mmin -5 2>/dev/null | head -1)
  if [ -n "$recent" ]; then echo "codex"; exit 0; fi
fi

# 6-7. CLI-on-PATH probes
has_codex=$(command -v codex >/dev/null 2>&1 && echo yes || echo no)
has_claude=$(command -v claude >/dev/null 2>&1 && echo yes || echo no)

if [ "$has_codex" = "yes" ] && [ "$has_claude" = "no" ]; then echo "codex"; exit 0; fi
if [ "$has_claude" = "yes" ]; then echo "claude-code"; exit 0; fi

# 8. Unknown
echo "detect-runtime.sh: unknown — no env vars set and neither codex nor claude on PATH. Set PURSUE_RUNTIME explicitly." >&2
exit 3
