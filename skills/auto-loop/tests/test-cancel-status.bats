#!/usr/bin/env bats

setup() {
  SKILL_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  DISPATCH="$SKILL_DIR/scripts/dispatch.sh"
  STATUS="$SKILL_DIR/scripts/status-reader.sh"
  CANCEL="$SKILL_DIR/scripts/cancel-loop.sh"
  TMPDIR=$(mktemp -d)
  ( cd "$TMPDIR" && git init -q && touch a && git add -A && git -c user.email=t@t -c user.name=t commit -qm init )
  export VD_AUTOLOOP_WORKSPACE="$TMPDIR"
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "status on no-loop workspace returns exit 2" {
  run "$STATUS" "$TMPDIR"
  [ "$status" -eq 2 ]
  echo "$output" | grep -q "no active vd:auto-loop"
}

@test "cancel on no-loop workspace is a clean no-op" {
  run "$CANCEL" "$TMPDIR"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "no active loop"
}

@test "status is read-only (no .auto-loop/ mutation)" {
  "$DISPATCH" "g" --verify "true" --max-iterations 3 --max-wallclock 30m >/dev/null

  before=$(find "$TMPDIR/.auto-loop" -type f -exec stat -f '%m %N' {} \; 2>/dev/null | sort)
  "$STATUS" "$TMPDIR" >/dev/null
  after=$(find "$TMPDIR/.auto-loop" -type f -exec stat -f '%m %N' {} \; 2>/dev/null | sort)

  [ "$before" = "$after" ]

  "$CANCEL" "$TMPDIR" >/dev/null
}

@test "cancel restores .claude/settings.local.json to pre-install state" {
  echo '{"foo": "bar"}' > "$TMPDIR/.claude/settings.local.json" 2>/dev/null || \
    { mkdir -p "$TMPDIR/.claude" && echo '{"foo": "bar"}' > "$TMPDIR/.claude/settings.local.json"; }
  before=$(cat "$TMPDIR/.claude/settings.local.json")

  "$DISPATCH" "g" --verify "true" --max-iterations 3 --max-wallclock 30m >/dev/null
  # Stop hook should now be present
  jq -e '.hooks.Stop' "$TMPDIR/.claude/settings.local.json" >/dev/null

  "$CANCEL" "$TMPDIR" >/dev/null
  after=$(cat "$TMPDIR/.claude/settings.local.json")

  # Restored
  [ "$(echo "$before" | jq -S .)" = "$(echo "$after" | jq -S .)" ]
}

@test "second --cancel is idempotent (no error)" {
  "$DISPATCH" "g" --verify "true" --max-iterations 3 --max-wallclock 30m >/dev/null
  "$CANCEL" "$TMPDIR" >/dev/null
  run "$CANCEL" "$TMPDIR"
  [ "$status" -eq 0 ]
}
