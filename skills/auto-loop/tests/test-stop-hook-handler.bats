#!/usr/bin/env bats

setup() {
  SKILL_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  HOOK="$SKILL_DIR/scripts/stop-hook-handler.sh"
  RW="$SKILL_DIR/scripts/state-rw.sh"
  TMPDIR=$(mktemp -d)
  ( cd "$TMPDIR" && git init -q && touch a && git add -A \
    && git -c user.email=t@t -c user.name=t commit -qm init )
  mkdir -p "$TMPDIR/.auto-loop"
  jq -n --argjson pid $$ \
        --arg sa "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --arg sid t --arg gt "test goal" --arg vf "true" \
        --argjson mi 5 --argjson mt 1000000 --arg mw "30m" \
        --argjson rp 70 --argjson mr 5 \
        --arg al "" --arg dn "" --arg sr "HEAD" \
        '{pid:$pid, started_at:$sa, session_id:$sid, goal_text:$gt, verify:$vf,
          max_iterations:$mi, max_tokens:$mt, max_wallclock:$mw,
          restart_at_context_pct:$rp, max_restarts:$mr,
          allow:$al, deny:$dn, start_ref:$sr}' > "$TMPDIR/.auto-loop/heartbeat.json"
  "$RW" seed "$TMPDIR/.auto-loop/goal-state.json"
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "no heartbeat → emit_allow_stop ({})" {
  rm -f "$TMPDIR/.auto-loop/heartbeat.json"
  cd "$TMPDIR"
  run bash "$HOOK" </dev/null
  [ "$status" -eq 0 ]
  echo "$output" | jq -e '.' >/dev/null   # valid JSON
  # No `decision: "approve"` (which would be schema-invalid for Claude Code).
  ! echo "$output" | jq -e '.decision == "approve"' >/dev/null
}

@test "stop_hook_active=true short-circuits to allow_stop" {
  cd "$TMPDIR"
  run bash -c "echo '{\"stop_hook_active\":true}' | bash $HOOK"
  [ "$status" -eq 0 ]
  echo "$output" | jq -e '.' >/dev/null
  ! echo "$output" | jq -e 'has("decision")' >/dev/null
}

@test "live heartbeat + pursuing state → emit_block with re-feed prompt" {
  cd "$TMPDIR"
  run bash "$HOOK" </dev/null
  [ "$status" -eq 0 ]
  echo "$output" | jq -e '.decision == "block"' >/dev/null
  echo "$output" | jq -e '.reason | contains("test goal")' >/dev/null
}

@test "iter cap fires graceful drain, not raw allow_stop" {
  cd "$TMPDIR"
  jq '.iteration = 5' "$TMPDIR/.auto-loop/goal-state.json" > "$TMPDIR/_st"
  "$RW" write "$TMPDIR/.auto-loop/goal-state.json" "$(cat $TMPDIR/_st)"
  run bash "$HOOK" </dev/null
  [ "$status" -eq 0 ]
  echo "$output" | jq -e '.decision == "block"' >/dev/null
  echo "$output" | jq -e '.reason | contains("Budget cap reached")' >/dev/null
  jq -e '.status == "budget-limited"' "$TMPDIR/.auto-loop/goal-state.json" >/dev/null
}

@test "wallclock cap fires drain even if iter under cap" {
  # Reset heartbeat with started_at way in the past + tiny wallclock
  jq '.started_at = "1970-01-01T00:00:00Z" | .max_wallclock = "1s"' \
     "$TMPDIR/.auto-loop/heartbeat.json" > "$TMPDIR/_hb"
  mv "$TMPDIR/_hb" "$TMPDIR/.auto-loop/heartbeat.json"
  cd "$TMPDIR"
  run bash "$HOOK" </dev/null
  [ "$status" -eq 0 ]
  echo "$output" | jq -e '.reason | contains("wallclock")' >/dev/null
}

@test "iteration counter increments per Stop-hook firing" {
  cd "$TMPDIR"
  bash "$HOOK" </dev/null >/dev/null
  bash "$HOOK" </dev/null >/dev/null
  iter=$(jq -r '.iteration' "$TMPDIR/.auto-loop/goal-state.json")
  [ "$iter" -eq 2 ]
}

@test "cancelled state → emit_allow_stop, no further work" {
  jq '.status = "cancelled"' "$TMPDIR/.auto-loop/goal-state.json" > "$TMPDIR/_st"
  "$RW" write "$TMPDIR/.auto-loop/goal-state.json" "$(cat $TMPDIR/_st)"
  cd "$TMPDIR"
  run bash "$HOOK" </dev/null
  [ "$status" -eq 0 ]
  ! echo "$output" | jq -e 'has("decision")' >/dev/null
}
