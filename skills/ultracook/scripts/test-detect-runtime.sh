#!/usr/bin/env bash
# test-detect-runtime.sh - truth-table regression guard for detect-runtime.sh (#60).
# Runs the detector under controlled env + PATH; asserts output and exit code.
# Exit 0 = all pass, 1 = any failure.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DETECT="${HERE}/detect-runtime.sh"

# Isolated bin with fake CLIs we toggle per-case; isolated empty HOME so the
# recency fallback never reads real ~/.codex/sessions.
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
BIN="${TMP}/bin"; mkdir -p "$BIN" "${TMP}/home/.codex/sessions"
make_cli() { printf '#!/bin/sh\nexit 0\n' > "${BIN}/$1"; chmod +x "${BIN}/$1"; }

pass=0; fail=0
# run "<expected_out>" "<expected_exit>" ENV... -- (env passed via leading VAR=val tokens)
run() {
  local desc="$1" exp_out="$2" exp_code="$3"; shift 3
  local out code
  # PATH = isolated fake-bin first, then system bins for bash/find/head. Real
  # codex (homebrew) / claude (~/.local) are NOT in /usr/bin:/bin → isolation holds.
  out="$(env -i HOME="${TMP}/home" PATH="${BIN}:/usr/bin:/bin" "$@" bash "$DETECT" 2>/dev/null)"; code=$?
  if [ "$out" = "$exp_out" ] && [ "$code" = "$exp_code" ]; then
    pass=$((pass+1)); # echo "ok   $desc"
  else
    fail=$((fail+1)); echo "FAIL $desc → got '$out' (exit $code), want '$exp_out' (exit $exp_code)"
  fi
}

# Cases with NO codex/claude on PATH unless added.
run "override codex-exec"        "codex-exec" 0 ULTRACOOK_RUNTIME=codex-exec
run "override claude-code"       "claude-code" 0 ULTRACOOK_RUNTIME=claude-code
run "CLAUDECODE only"            "claude-code" 0 CLAUDECODE=1
run "CLAUDE_PROJECT_DIR only"    "claude-code" 0 CLAUDE_PROJECT_DIR=/x
run "CLAUDE_CODE_ENTRYPOINT"     "claude-code" 0 CLAUDE_CODE_ENTRYPOINT=cli
run "CODEX only"                 "codex" 0 CODEX_SESSION_ID=abc
run "CODEX + exec contract"      "codex-exec" 0 CODEX_SESSION_ID=abc ULTRACOOK_EXEC=1
run "both → CLAUDE wins"         "claude-code" 0 CLAUDECODE=1 CODEX_SESSION_ID=abc
run "unknown (no env, no PATH)"  "" 3

# PATH-probe cases (no env signals).
make_cli codex
run "codex on PATH only"         "codex" 0
run "codex on PATH + exec"       "codex-exec" 0 ULTRACOOK_EXEC=1
make_cli claude
run "both on PATH → claude"      "claude-code" 0

echo "detect-runtime truth-table: pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
