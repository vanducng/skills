#!/usr/bin/env bats

setup() {
  SKILL_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  GATE="$SKILL_DIR/scripts/check-completion-gate.sh"
  RW="$SKILL_DIR/scripts/state-rw.sh"
  TMPDIR=$(mktemp -d)
  ( cd "$TMPDIR" && git init -q && touch a && git add -A && git -c user.email=t@t -c user.name=t commit -qm init )
  mkdir -p "$TMPDIR/.auto-loop"
  jq -n --argjson pid $$ --arg sa "2026-01-01T00:00:00Z" --arg sid t \
        --arg gt "test goal" --arg vf "true" --argjson mi 5 --argjson mt 1 \
        --arg mw "10m" --argjson rp 70 --argjson mr 5 \
        --arg al "" --arg dn "" --arg sr "HEAD" \
        '{pid:$pid, started_at:$sa, session_id:$sid, goal_text:$gt, verify:$vf, max_iterations:$mi, max_tokens:$mt, max_wallclock:$mw, restart_at_context_pct:$rp, max_restarts:$mr, allow:$al, deny:$dn, start_ref:$sr}' > "$TMPDIR/.auto-loop/heartbeat.json"
  "$RW" seed "$TMPDIR/.auto-loop/goal-state.json"
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "verifier-fail flips state to unmet" {
  run "$GATE" 1 "false" "$TMPDIR"
  [ "$status" -ne 0 ]
  jq -e '.status == "unmet"' "$TMPDIR/.auto-loop/goal-state.json" >/dev/null
  jq -e '.verifier_result == "fail"' "$TMPDIR/.auto-loop/goal-state.json" >/dev/null
}

@test "gate logs to gate-history.jsonl" {
  "$GATE" 1 "false" "$TMPDIR" || true
  [ -f "$TMPDIR/.auto-loop/gate-history.jsonl" ]
  tail -n1 "$TMPDIR/.auto-loop/gate-history.jsonl" | jq -e '.iter == 1' >/dev/null
}

@test "verifier rejects shell injection cleanly" {
  # `;rm -rf` is just a command that fails; bash -c isolates it.
  run "$GATE" 1 'echo safe; false' "$TMPDIR"
  [ "$status" -ne 0 ]
  # Workspace should be intact.
  [ -f "$TMPDIR/a" ]
}

@test "missing audit subagent → defaults to unmet (gate stays closed)" {
  # Verifier passes but no `claude` headless available in test env →
  # spawn-audit-subagent returns default unmet → gate closes.
  run "$GATE" 1 "true" "$TMPDIR"
  [ "$status" -ne 0 ]
  jq -e '.status == "unmet"' "$TMPDIR/.auto-loop/goal-state.json" >/dev/null
  jq -e '.verifier_result == "pass"' "$TMPDIR/.auto-loop/goal-state.json" >/dev/null
}
