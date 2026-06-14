#!/usr/bin/env bash
# Tests for eval-dod.sh. Run: bash skills/cook/scripts/eval-dod.test.sh
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$DIR/eval-dod.sh"
pass=0; fail=0
ok()  { pass=$((pass+1)); echo "  ✓ $1"; }
bad() { fail=$((fail+1)); echo "  ✗ $1"; }
assert_exit() { # <expected> <desc> -- cmd...
  local want="$1" desc="$2"; shift 2
  "$@" >/dev/null 2>&1; local got=$?
  [ "$got" = "$want" ] && ok "$desc" || bad "$desc (exit $got, want $want)"
}

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/pass.md" <<'EOF'
## Definition of Done
- cmd_exits_zero: true
- test_suite_passes: python3 -c "assert 1+1==2"
- shell: echo hi
## Out of Scope
EOF

cat > "$TMP/fail.md" <<'EOF'
## Definition of Done
- cmd_exits_zero: true
- shell: false
EOF

cat > "$TMP/none.md" <<'EOF'
## Goal
no DoD here
EOF

cat > "$TMP/bad.md" <<'EOF'
## Definition of Done
- bogus_type: whatever
- cmd_exits_zero:
EOF

cat > "$TMP/manual.md" <<'EOF'
## Definition of Done
- manual_confirm: did you eyeball the UI?
EOF

echo "eval-dod tests:"
assert_exit 0 "all-pass plan → exit 0"            bash "$RUNNER" "$TMP/pass.md"
assert_exit 1 "one failing verifier → exit 1"      bash "$RUNNER" "$TMP/fail.md"
assert_exit 1 "no DoD block → exit 1 (fallback)"   bash "$RUNNER" "$TMP/none.md"
assert_exit 2 "missing plan file → exit 2"         bash "$RUNNER" "$TMP/nope.md"
assert_exit 0 "lint clean block → exit 0"          bash "$RUNNER" --lint "$TMP/pass.md"
assert_exit 1 "lint bad block → exit 1"            bash "$RUNNER" --lint "$TMP/bad.md"
assert_exit 1 "manual_confirm needs user → exit 1" bash "$RUNNER" "$TMP/manual.md"
assert_exit 0 "single --type pass → exit 0"        bash "$RUNNER" --type cmd_exits_zero --arg "true"
assert_exit 1 "single --type fail → exit 1"        bash "$RUNNER" --type cmd_exits_zero --arg "false"
assert_exit 1 "workflow-level type rejected"       bash "$RUNNER" --type ci_green --arg "1"

# content check: comments + blanks ignored, http_status parses
cat > "$TMP/mix.md" <<'EOF'
## Definition of Done
<!-- ignore me -->
# also ignore

- cmd_exits_zero: true
## Next
- shell: should-not-run
EOF
out="$(bash "$RUNNER" "$TMP/mix.md" 2>&1)"
echo "$out" | grep -q "1/1 verifiers pass" && ok "section boundary + comment skipping" || bad "section boundary + comment skipping"

echo "---"
echo "eval-dod: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
