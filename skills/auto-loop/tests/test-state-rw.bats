#!/usr/bin/env bats

setup() {
  SKILL_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  RW="$SKILL_DIR/scripts/state-rw.sh"
  TMPDIR=$(mktemp -d)
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "seed → read round-trips a valid pursuing state" {
  "$RW" seed "$TMPDIR/state.json"
  run "$RW" read "$TMPDIR/state.json"
  [ "$status" -eq 0 ]
  echo "$output" | jq -e '.status == "pursuing"' >/dev/null
  echo "$output" | jq -e '.iteration == 0' >/dev/null
  echo "$output" | jq -e '.schema_version == 1' >/dev/null
}

@test "write rejects missing status field" {
  bad='{"schema_version":1,"iteration":0,"evidence":[],"blockers":[],"next_action":"x","tokens_used":0,"started_at":"2026-01-01T00:00:00Z","last_update":"2026-01-01T00:00:00Z","last_diff_signature":""}'
  run "$RW" write "$TMPDIR/state.json" "$bad"
  [ "$status" -ne 0 ]
  [ ! -f "$TMPDIR/state.json" ]
}

@test "write rejects bogus enum value" {
  bad='{"schema_version":1,"iteration":0,"status":"bogus","evidence":[],"blockers":[],"next_action":"x","tokens_used":0,"started_at":"2026-01-01T00:00:00Z","last_update":"2026-01-01T00:00:00Z","last_diff_signature":""}'
  run "$RW" write "$TMPDIR/state.json" "$bad"
  [ "$status" -ne 0 ]
}

@test "write rejects unsupported schema_version" {
  bad='{"schema_version":99,"iteration":0,"status":"pursuing","evidence":[],"blockers":[],"next_action":"x","tokens_used":0,"started_at":"2026-01-01T00:00:00Z","last_update":"2026-01-01T00:00:00Z","last_diff_signature":""}'
  run "$RW" write "$TMPDIR/state.json" "$bad"
  [ "$status" -ne 0 ]
}

@test "write succeeds with valid payload" {
  good='{"schema_version":1,"iteration":3,"status":"pursuing","evidence":["foo"],"blockers":[],"next_action":"step","tokens_used":1000,"started_at":"2026-01-01T00:00:00Z","last_update":"2026-01-01T00:00:01Z","last_diff_signature":"abc123"}'
  run "$RW" write "$TMPDIR/state.json" "$good"
  [ "$status" -eq 0 ]
  [ -f "$TMPDIR/state.json" ]
  jq -e '.iteration == 3' "$TMPDIR/state.json" >/dev/null
}

@test "atomic write leaves no partial file on validation failure" {
  bad='{"not even close": "json structure missing all fields"}'
  run "$RW" write "$TMPDIR/state.json" "$bad"
  [ "$status" -ne 0 ]
  [ ! -f "$TMPDIR/state.json" ]
}
