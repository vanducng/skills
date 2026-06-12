#!/usr/bin/env bash
# write-compaction-summary.sh — render compaction-summary.template.md into
# .auto-loop/compaction-{iter}.md using current state + recent logs.
#
# Usage: write-compaction-summary.sh <workspace>
# Stdout: path to the rendered summary file.

set -uo pipefail

ws="${1:?workspace required}"
cd "$ws"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/_state-dir.sh"
state_file="$state_dir/goal-state.json"
heartbeat="$state_dir/heartbeat.json"
gate_log="$state_dir/gate-history.jsonl"
restart_log="$state_dir/restart-history.jsonl"

[[ -f "$state_file" ]] || { echo "no state file"; exit 1; }

iter=$(jq -r '.iteration // 0' "$state_file")
status=$(jq -r '.status // "pursuing"' "$state_file")
vr=$(jq -r '.verifier_result // "not-run"' "$state_file")
av=$(jq -r '.audit_vote // "not-run"' "$state_file")
na=$(jq -r '.next_action // ""' "$state_file")
restart_count=$(jq -r '.restart_count // 0' "$state_file")
goal=$(jq -r '.goal_text // ""' "$heartbeat" 2>/dev/null || echo "")

verifier_log="$state_dir/verifier-${iter}.log"
verifier_tail=$(tail -n 30 "$verifier_log" 2>/dev/null || echo "(no verifier log)")
audit_tail=$(ls -1 "$state_dir"/audit-*.json 2>/dev/null | tail -n 3 | xargs -I{} cat {} 2>/dev/null || echo "(none)")

# Files hot-list: most-touched files in the loop's git diff
files_hot=$(git -C "$ws" log --name-only --pretty=format: 2>/dev/null \
            | grep -v '^$' | sort | uniq -c | sort -rn | head -n 10 || echo "")

out="$state_dir/compaction-${iter}.md"
template="$SKILL_DIR/templates/compaction-summary.template.md"

awk -v goal="$goal" \
    -v iter="$iter" \
    -v status="$status" \
    -v vr="$vr" \
    -v av="$av" \
    -v rc="$restart_count" \
    -v vlog="$verifier_tail" \
    -v atail="$audit_tail" \
    -v files="$files_hot" \
    -v na="$na" \
    -v skill="$SKILL_DIR" '
{
  gsub(/\{GOAL\}/, goal)
  gsub(/\{ITERATION\}/, iter)
  gsub(/\{STATUS\}/, status)
  gsub(/\{VERIFIER_RESULT\}/, vr)
  gsub(/\{AUDIT_VOTE\}/, av)
  gsub(/\{RESTART_COUNT\}/, rc)
  gsub(/\{VERIFIER_TAIL\}/, vlog)
  gsub(/\{AUDIT_TAIL\}/, atail)
  gsub(/\{FILES_HOT_LIST\}/, files)
  gsub(/\{NEXT_ACTION\}/, na)
  gsub(/\{SKILL_DIR\}/, skill)
  print
}' "$template" > "$out"

# Append restart event
now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
jq -nc --arg t "$now" --argjson i "$iter" --arg s "$status" \
  '{at:$t, iter:$i, status:$s, event:"compaction-summary-written"}' >> "$restart_log"

echo "$out"
