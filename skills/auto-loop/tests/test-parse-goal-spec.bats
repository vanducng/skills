#!/usr/bin/env bats

setup() {
  SKILL_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  PARSER="$SKILL_DIR/scripts/parse-goal-spec.sh"
  TMPDIR=$(mktemp -d)
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "valid template parses with all fields" {
  run "$PARSER" "$SKILL_DIR/templates/goal.template.md"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "^GOAL='"
  echo "$output" | grep -q "^VERIFY='"
  echo "$output" | grep -q "^MAX_ITERATIONS=30"
  echo "$output" | grep -q "^MAX_WALLCLOCK='2h'"
}

@test "missing # Goal block exits non-zero" {
  cat > "$TMPDIR/bad.md" <<EOF
# Verify
verify: \`true\`
EOF
  run "$PARSER" "$TMPDIR/bad.md"
  [ "$status" -ne 0 ]
}

@test "missing verify: exits non-zero" {
  cat > "$TMPDIR/bad.md" <<EOF
# Goal
do something
EOF
  run "$PARSER" "$TMPDIR/bad.md"
  [ "$status" -ne 0 ]
}

@test "underscores in numbers are stripped" {
  cat > "$TMPDIR/g.md" <<EOF
# Goal
x

# Verify
verify: \`true\`

# Caps
max_tokens: 1_500_000
EOF
  run "$PARSER" "$TMPDIR/g.md"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "^MAX_TOKENS=1500000"
}

@test "unknown keys are silently ignored" {
  cat > "$TMPDIR/g.md" <<EOF
# Goal
x

# Verify
verify: \`true\`

# Future
exotic_field: yes
EOF
  run "$PARSER" "$TMPDIR/g.md"
  [ "$status" -eq 0 ]
}

@test "missing file exits with code 2" {
  run "$PARSER" "$TMPDIR/does-not-exist.md"
  [ "$status" -eq 2 ]
}
