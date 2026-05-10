#!/usr/bin/env bash
# spawn-audit-subagent.sh — render audit prompt and invoke a fresh-context subagent.
#
# Spawns via headless `claude -p` if available; falls back to a stub vote when not
# (subagent invocation is impossible from a non-Claude-Code shell — vote=unmet).
# Recursion guard: VD_AUTOLOOP_DEPTH must be 0 or unset on entry; child sees
# VD_AUTOLOOP_DEPTH=1 and must refuse to spawn another loop.
#
# Usage: spawn-audit-subagent.sh <iter> <verify-cmd> <workspace>
# Stdout: JSON `{"vote": "...", "reason": "...", "missing": [...]}`
# Persists copy at .auto-loop/audit-{iter}.json

set -uo pipefail

iter="${1:?iter required}"
verify_cmd="${2:?verify-cmd required}"
ws="${3:?workspace required}"

cd "$ws"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
state_dir=".auto-loop"
audit_file="$state_dir/audit-${iter}.json"
gate_log="$state_dir/gate-history.jsonl"

# --- Recursion guard ---
depth="${VD_AUTOLOOP_DEPTH:-0}"
if [[ "$depth" -gt 0 ]]; then
  echo '{"vote":"unmet","reason":"recursion guard: refusing nested audit","missing":[]}' \
    | tee "$audit_file"
  exit 0
fi

# --- Compose prompt ---
template="$SKILL_DIR/templates/audit-prompt.md"
heartbeat="$state_dir/heartbeat.json"
state_file="$state_dir/goal-state.json"

goal=$(jq -r '.goal_text // ""' "$heartbeat" 2>/dev/null || echo "")
verifier_log="$state_dir/verifier-${iter}.log"
verifier_result=$(jq -r '.verifier_result // "not-run"' "$state_file" 2>/dev/null || echo "not-run")
verifier_tail=$(tail -n 40 "$verifier_log" 2>/dev/null || echo "(no log)")

start_ref=$(jq -r '.start_ref // "HEAD"' "$heartbeat" 2>/dev/null || echo "HEAD")
diff_stat=$(git -C "$ws" diff --stat "$start_ref" 2>/dev/null || echo "(no git or no diff)")
files_changed=$(git -C "$ws" diff --name-only "$start_ref" 2>/dev/null || echo "")
files_count=$(printf '%s\n' "$files_changed" | grep -c . || echo 0)
files_list=$(printf '%s\n' "$files_changed" | head -n 30)

gate_tail=$(tail -n 5 "$gate_log" 2>/dev/null || echo "(empty)")

prompt=$(awk -v goal="$goal" \
             -v vr="$verifier_result" \
             -v verify="$verify_cmd" \
             -v vlog="$verifier_tail" \
             -v fcc="$files_count" \
             -v flist="$files_list" \
             -v dstat="$diff_stat" \
             -v ghist="$gate_tail" '
{
  gsub(/\{GOAL\}/, goal)
  gsub(/\{VERIFIER_RESULT\}/, vr)
  gsub(/\{VERIFY\}/, verify)
  gsub(/\{VERIFIER_TAIL\}/, vlog)
  gsub(/\{FILES_CHANGED_COUNT\}/, fcc)
  gsub(/\{FILES_LIST\}/, flist)
  gsub(/\{DIFF_STAT\}/, dstat)
  gsub(/\{GATE_HISTORY_TAIL\}/, ghist)
  print
}' "$template")

# --- Invoke subagent ---
# Hard timeout: a hung audit subagent must not freeze the parent's Stop hook.
# Restrict tools to read-only — the audit prompt says read-only, this enforces it
# at the SDK level rather than relying on the model honouring instructions.
TIMEOUT_BIN=""
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_BIN="timeout 120"
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_BIN="gtimeout 120"
fi

vote_json=""
if command -v claude >/dev/null 2>&1; then
  # Headless run; force fresh context (no --resume, no --include-partial).
  raw=$(VD_AUTOLOOP_DEPTH=1 $TIMEOUT_BIN claude -p \
        --allowedTools "Read,Glob,Grep,Bash(git diff:*),Bash(git log:*),Bash(git status:*),Bash(cat:*),Bash(ls:*)" \
        "$prompt" 2>/dev/null || true)
  # Extract JSON (last JSON-looking line).
  vote_json=$(printf '%s\n' "$raw" | grep -oE '\{[^{}]*"vote"[^{}]*\}' | tail -n 1 || true)
fi

# Defensive defaults
if [[ -z "$vote_json" ]]; then
  vote_json='{"vote":"unmet","reason":"audit subagent unavailable; defaulting to unmet (gate stays closed)","missing":[]}'
fi

# Validate parseability
if ! printf '%s' "$vote_json" | jq -e '.vote' >/dev/null 2>&1; then
  vote_json='{"vote":"unmet","reason":"audit response unparseable","missing":[]}'
fi

# Coerce vote into allowed enum
vote_value=$(printf '%s' "$vote_json" | jq -r '.vote')
case "$vote_value" in
  achieved|unmet|blocked|thrashing) ;;
  *) vote_json='{"vote":"unmet","reason":"audit returned invalid vote","missing":[]}' ;;
esac

printf '%s\n' "$vote_json" > "$audit_file"
printf '%s\n' "$vote_json"
