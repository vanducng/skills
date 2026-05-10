#!/usr/bin/env bats

setup() {
  SKILL_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  CAPS="$SKILL_DIR/scripts/check-budget-caps.sh"
  RW="$SKILL_DIR/scripts/state-rw.sh"
  TMPDIR=$(mktemp -d)
  mkdir -p "$TMPDIR/.auto-loop"
  "$RW" seed "$TMPDIR/.auto-loop/goal-state.json"
}

teardown() {
  rm -rf "$TMPDIR"
}

write_heartbeat() {
  # write_heartbeat <max_iter> <max_tokens> <max_wallclock> <started_at>
  local mi="$1" mt="$2" mw="$3" sa="$4"
  jq -n --argjson pid $$ --arg sa "$sa" --arg sid t \
        --arg gt "g" --arg vf "true" --argjson mi "$mi" --argjson mt "$mt" \
        --arg mw "$mw" --argjson rp 70 --argjson mr 5 \
        --arg al "" --arg dn "" --arg sr "HEAD" \
        '{pid:$pid, started_at:$sa, session_id:$sid, goal_text:$gt, verify:$vf, max_iterations:$mi, max_tokens:$mt, max_wallclock:$mw, restart_at_context_pct:$rp, max_restarts:$mr, allow:$al, deny:$dn, start_ref:$sr}' > "$TMPDIR/.auto-loop/heartbeat.json"
}

bump_iter() {
  local n="$1"
  jq --argjson n "$n" '.iteration = $n' "$TMPDIR/.auto-loop/goal-state.json" > "$TMPDIR/_tmp"
  "$RW" write "$TMPDIR/.auto-loop/goal-state.json" "$(cat $TMPDIR/_tmp)"
}

@test "iteration cap fires when iter >= max_iterations" {
  write_heartbeat 3 1000000 "10m" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  bump_iter 3
  run "$CAPS" "$TMPDIR"
  [ "$status" -eq 1 ]
  echo "$output" | jq -e '.reason == "iterations"' >/dev/null
  jq -e '.status == "budget-limited"' "$TMPDIR/.auto-loop/goal-state.json" >/dev/null
}

@test "wallclock cap fires when elapsed exceeds limit" {
  write_heartbeat 100 1000000 "1s" "1970-01-01T00:00:00Z"
  run "$CAPS" "$TMPDIR"
  [ "$status" -eq 1 ]
  echo "$output" | jq -e '.reason == "wallclock"' >/dev/null
}

@test "no cap firing under budget" {
  write_heartbeat 100 1000000000 "10h" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  bump_iter 1
  run "$CAPS" "$TMPDIR"
  [ "$status" -eq 0 ]
}

@test "wallclock duration parser handles compound forms" {
  # 4h30m → 16200s; if started_at far in past → fires
  write_heartbeat 100 1000000000 "4h30m" "1970-01-01T00:00:00Z"
  run "$CAPS" "$TMPDIR"
  [ "$status" -eq 1 ]
  echo "$output" | jq -e '.reason == "wallclock"' >/dev/null
}
