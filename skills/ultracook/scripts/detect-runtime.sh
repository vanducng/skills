#!/usr/bin/env bash
# detect-runtime.sh — identify which agent runtime is invoking ultracook.
#
# Stdout: "claude-code" | "codex" | "codex-exec"
# Stderr + exit 3: "unknown" when no signal is found
#
# Detection precedence (top → bottom):
#   1. $ULTRACOOK_RUNTIME override (claude-code | codex | codex-exec)
#   2. Broadened CLAUDE signal present → claude-code
#      (CLAUDE wins when CODEX is ALSO set: CODEX_SESSION_ID leaks into child
#       shells via codex `shell_environment_policy.inherit=all`, whereas the
#       CLAUDE_CODE_* vars are set by the active Claude process. We emit a
#       one-line stderr note when both are seen so the rare reverse case
#       (codex launched from a claude shell) can be corrected with
#       ULTRACOOK_RUNTIME=codex.)
#   3. CODEX signal (CODEX_SESSION_ID) → codex, or codex-exec when the explicit
#      exec contract ($ULTRACOOK_EXEC=1) is set. No env var distinguishes
#      `codex exec` from `codex` TUI in codex-cli ≤0.137, so exec mode is an
#      explicit caller contract — never inferred from TTY/process state.
#   4. codex on PATH AND claude NOT on PATH → codex
#   5. claude on PATH → claude-code
#   6. Codex session recency-fallback (last resort): a Codex session JSONL
#      modified within 5 min + codex on PATH → codex. Demoted below PATH probes
#      because it manufactures codex false-positives for anyone who used codex
#      recently while now in Claude Code.
#   7. else → unknown

set -o pipefail

# 1. Explicit override.
case "${ULTRACOOK_RUNTIME:-}" in
  claude-code|codex|codex-exec) echo "$ULTRACOOK_RUNTIME"; exit 0 ;;
esac

# Gather signals. CLAUDE set is broadened beyond the v0.2 hook-only vars
# (CLAUDE_PROJECT_DIR / CLAUDE_TOOL_USE_ID) to include the vars the Claude Code
# CLI exports into every Bash subprocess.
CLAUDE_SIGNAL=""
CODEX_SIGNAL=""
[ -n "${CLAUDE_PROJECT_DIR:-}" ] || [ -n "${CLAUDE_TOOL_USE_ID:-}" ] || \
  [ -n "${CLAUDECODE:-}" ] || [ -n "${CLAUDE_CODE_SESSION_ID:-}" ] || \
  [ -n "${CLAUDE_CODE_ENTRYPOINT:-}" ] && CLAUDE_SIGNAL="yes"
[ -n "${CODEX_SESSION_ID:-}" ] && CODEX_SIGNAL="yes"

# Exec contract — only meaningful in a codex context.
EXEC=""
case "${ULTRACOOK_EXEC:-}" in 1|true|yes) EXEC="yes" ;; esac

# 2. CLAUDE wins (even when CODEX also set — see header).
if [ -n "$CLAUDE_SIGNAL" ]; then
  if [ -n "$CODEX_SIGNAL" ]; then
    echo "detect-runtime.sh: both CLAUDE_CODE_* and CODEX_SESSION_ID present; assuming claude-code (CODEX_SESSION_ID commonly leaks via inherit=all). Override with ULTRACOOK_RUNTIME=codex if this is a Codex session." >&2
  fi
  echo "claude-code"; exit 0
fi

# 3. CODEX env signal.
if [ -n "$CODEX_SIGNAL" ]; then
  [ -n "$EXEC" ] && { echo "codex-exec"; exit 0; }
  echo "codex"; exit 0
fi

# 4-5. CLI-on-PATH probes.
has_codex=$(command -v codex >/dev/null 2>&1 && echo yes || echo no)
has_claude=$(command -v claude >/dev/null 2>&1 && echo yes || echo no)

if [ "$has_codex" = "yes" ] && [ "$has_claude" = "no" ]; then
  [ -n "$EXEC" ] && { echo "codex-exec"; exit 0; }
  echo "codex"; exit 0
fi
if [ "$has_claude" = "yes" ]; then echo "claude-code"; exit 0; fi

# 6. Codex recency fallback (last resort).
if command -v codex >/dev/null 2>&1; then
  recent=$(find "$HOME/.codex/sessions" -maxdepth 2 -name '*.jsonl' -mmin -5 2>/dev/null | head -1)
  if [ -n "$recent" ]; then
    [ -n "$EXEC" ] && { echo "codex-exec"; exit 0; }
    echo "codex"; exit 0
  fi
fi

# 7. Unknown.
echo "detect-runtime.sh: unknown — no env vars set and neither codex nor claude on PATH. Set ULTRACOOK_RUNTIME explicitly." >&2
exit 3
