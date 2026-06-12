#!/usr/bin/env bash
# drift-watchdog.sh — detect stagnation (no file changes for 3 iters) or thrashing
# (same file edited 5+ times). Escalates by spawning audit subagent with a diagnose
# prompt. On vote=blocked → state.status=blocked. On vote=thrashing → next-iter
# prompt gets an anti-thrash note.
#
# Usage: drift-watchdog.sh <workspace>
# Stdout (when escalation needed): JSON `{"action": "blocked|thrashing|none", "note": "..."}`
# Exit code: 0 always (this is advisory; never aborts the loop).

set -uo pipefail

ws="${1:?workspace required}"
cd "$ws"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_state-dir.sh"
state_file="$state_dir/goal-state.json"
heartbeat="$state_dir/heartbeat.json"
sig_log="$state_dir/diff-signatures.log"
edits_log="$state_dir/file-edits.log"

[[ -f "$state_file" ]] || { echo '{"action":"none"}'; exit 0; }

iter=$(jq -r '.iteration // 0' "$state_file")
sig=$(jq -r '.last_diff_signature // ""' "$state_file")

# Append current signature
echo "$iter $sig" >> "$sig_log"

# --- Stagnation: same signature 3 iters in a row ---
last3=$(tail -n 3 "$sig_log" | awk '{print $2}' | sort -u | wc -l | tr -d ' ')
if [[ "$last3" == "1" ]] && (( $(wc -l < "$sig_log") >= 3 )); then
  # Last 3 entries identical → stagnation
  audit=$(VD_AUTOLOOP_DEPTH="${VD_AUTOLOOP_DEPTH:-0}" \
          bash "$SCRIPT_DIR/spawn-audit-subagent.sh" "$iter" \
          "$(jq -r '.verify // ""' "$heartbeat" 2>/dev/null)" "$ws" 2>/dev/null \
          || echo '{"vote":"unmet"}')
  vote=$(printf '%s' "$audit" | jq -r '.vote // "unmet"')
  if [[ "$vote" == "blocked" ]]; then
    now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    new_state=$(jq --arg lu "$now" \
                   '.status = "blocked"
                    | .next_action = "drift watchdog: stagnation; audit voted blocked"
                    | .last_update = $lu' \
                   "$state_file")
    bash "$SCRIPT_DIR/state-rw.sh" write "$state_file" "$new_state"
    jq -nc '{action:"blocked", note:"3 iters with no diff change; audit voted blocked"}'
    exit 0
  fi
fi

# --- Thrashing: same file edited 5+ times ---
# Track files touched this iter (best-effort using last commit / dirty tree)
touched=$(git -C "$ws" status --porcelain 2>/dev/null | awk '{print $2}' || true)
for f in $touched; do
  echo "$iter $f" >> "$edits_log"
done

if [[ -s "$edits_log" ]]; then
  thrash_file=$(awk '{print $2}' "$edits_log" | sort | uniq -c | sort -rn | head -n 1 || true)
  count=$(printf '%s' "$thrash_file" | awk '{print $1}')
  fname=$(printf '%s' "$thrash_file" | awk '{print $2}')
  if [[ -n "${count:-}" ]] && [[ "$count" -ge 5 ]]; then
    jq -nc --arg f "$fname" --argjson c "$count" \
      '{action:"thrashing", note:("file " + $f + " edited " + ($c|tostring) + " times; advise structural shift")}'
    exit 0
  fi
fi

echo '{"action":"none"}'
exit 0
