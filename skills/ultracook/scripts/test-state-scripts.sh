#!/usr/bin/env bash
# test-state-scripts.sh - self-contained tests for update-state.sh, status.sh, kill.sh.
# Run: bash skills/ultracook/scripts/test-state-scripts.sh   (exit 0 = all pass)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT

PASS=0
FAIL=0

check() { # check <name> <expected-exit> <actual-exit>
  if [ "$2" -eq "$3" ]; then PASS=$((PASS+1)); echo "ok   $1"; else FAIL=$((FAIL+1)); echo "FAIL $1 (expected exit $2, got $3)"; fi
}

expect_grep() { # expect_grep <name> <pattern> <file>
  if grep -q "$2" "$3"; then PASS=$((PASS+1)); echo "ok   $1"; else FAIL=$((FAIL+1)); echo "FAIL $1 (pattern '$2' not found)"; fi
}

INIT_JSON='{"goal": "test goal", "mode": "pipeline", "autonomy": "semi", "stages": [{"skill": "plan", "status": "pending", "done_when": "plan approved"}, {"skill": "cook", "status": "pending", "done_when": "DoD passes"}], "iteration_count": 0, "terminal": null, "terminal_reason": null}'

# --- update-state.sh ---

echo "$INIT_JSON" | bash "$SCRIPT_DIR/update-state.sh" init "$TMPD/g1" >/dev/null 2>&1
check "init creates state.json" 0 $?
[ -f "$TMPD/g1/state.json" ]; check "state.json exists after init" 0 $?

echo "$INIT_JSON" | bash "$SCRIPT_DIR/update-state.sh" init "$TMPD/g1" >/dev/null 2>&1
check "double init refused" 2 $?

echo '{"iteration_count": 3, "stages": [{"skill": "plan", "status": "done", "done_when": "plan approved", "evidence": "approved"}, {"skill": "cook", "status": "running", "done_when": "DoD passes"}]}' \
  | bash "$SCRIPT_DIR/update-state.sh" patch "$TMPD/g1" >/dev/null 2>&1
check "patch merges" 0 $?
expect_grep "patch applied iteration_count" '"iteration_count": 3' "$TMPD/g1/state.json"
expect_grep "patch auto-sets updated_at" '"updated_at"' "$TMPD/g1/state.json"

echo '{"terminal": "bogus"}' | bash "$SCRIPT_DIR/update-state.sh" patch "$TMPD/g1" >/dev/null 2>&1
check "invalid terminal rejected" 4 $?

echo '{"version": 3}' | bash "$SCRIPT_DIR/update-state.sh" patch "$TMPD/g1" >/dev/null 2>&1
check "invalid version rejected" 4 $?

touch "$TMPD/g1/state.json.tmp"
echo '{"iteration_count": 4}' | bash "$SCRIPT_DIR/update-state.sh" patch "$TMPD/g1" >/dev/null 2>&1
check "crash-recovery tmp guard refuses" 3 $?
rm -f "$TMPD/g1/state.json.tmp"

bash "$SCRIPT_DIR/update-state.sh" patch "$TMPD/missing" </dev/null >/dev/null 2>&1
check "patch on missing goal dir refused" 2 $?

# --- status.sh ---

mkdir -p "$TMPD/corrupt" "$TMPD/legacy" "$TMPD/malformed"
echo '{"trunc' > "$TMPD/corrupt/state.json"
echo '{"version": 1, "terminal": null, "current_phase": "executing"}' > "$TMPD/legacy/state.json"
echo '{"version": 2, "stages": ["plan"], "terminal": null}' > "$TMPD/malformed/state.json"

OUT="$TMPD/status.out"
bash "$SCRIPT_DIR/status.sh" "$TMPD" > "$OUT" 2>&1
check "status base listing exits 0 despite bad files" 0 $?
expect_grep "good goal listed" "g1.*in-progress.*stage 1/2" "$OUT"
expect_grep "corrupt goal reported, not fatal" "corrupt.*unreadable" "$OUT"
expect_grep "legacy v1 flagged not resumable" "legacy.*legacy-v1" "$OUT"
expect_grep "malformed stages tolerated" "malformed" "$OUT"

bash "$SCRIPT_DIR/status.sh" "$TMPD/g1" > "$OUT" 2>&1
check "status detail exits 0" 0 $?
expect_grep "detail shows done-when" "done-when: DoD passes" "$OUT"
expect_grep "detail shows evidence" "evidence: approved" "$OUT"

bash "$SCRIPT_DIR/status.sh" "$TMPD/nope" >/dev/null 2>&1
check "status on missing path refused" 2 $?

# --- kill.sh ---

OUT="$TMPD/kill.out"
bash "$SCRIPT_DIR/kill.sh" "$TMPD/g1" --reason "test abandon" > "$OUT" 2>&1
check "kill marks abandoned" 0 $?
expect_grep "terminal written" '"terminal": "abandoned"' "$TMPD/g1/state.json"
expect_grep "reason written" '"terminal_reason": "test abandon"' "$TMPD/g1/state.json"

bash "$SCRIPT_DIR/kill.sh" "$TMPD/g1" --reason "again" >/dev/null 2>&1
check "kill refuses on already-terminal" 3 $?
expect_grep "original reason preserved" '"terminal_reason": "test abandon"' "$TMPD/g1/state.json"

bash "$SCRIPT_DIR/kill.sh" "$TMPD/g1" >/dev/null 2>&1
check "kill without --reason refused" 2 $?

bash "$SCRIPT_DIR/kill.sh" "$TMPD/nope" --reason "x" >/dev/null 2>&1
check "kill on missing goal refused" 2 $?

echo
echo "passed=$PASS failed=$FAIL"
[ "$FAIL" -eq 0 ]
