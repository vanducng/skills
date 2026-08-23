#!/usr/bin/env bash
# test-state-scripts.sh - exercise update-state / status / kill (schema v2).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPDATE="${SCRIPT_DIR}/update-state.sh"
STATUS="${SCRIPT_DIR}/status.sh"
KILL="${SCRIPT_DIR}/kill.sh"

chmod +x "$UPDATE" "$STATUS" "$KILL"

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/ultracook-state.XXXXXX")"
trap 'rm -rf "$WORKDIR"' EXIT

pass=0
fail=0
assert() {
  local name="$1" rc="$2" expect="$3"
  if [ "$rc" -eq "$expect" ]; then
    echo "OK   $name"
    pass=$((pass + 1))
  else
    echo "FAIL $name (exit $rc, want $expect)"
    fail=$((fail + 1))
  fi
}

assert_grep() {
  local name="$1" hay="$2" needle="$3"
  if printf '%s' "$hay" | grep -q "$needle"; then
    echo "OK   $name"
    pass=$((pass + 1))
  else
    echo "FAIL $name (missing '$needle')"
    echo "$hay" | sed 's/^/      /'
    fail=$((fail + 1))
  fi
}

sample_state() {
  local goal="${1:-demo goal}"
  python3 - "$goal" <<'PY'
import json, sys
print(json.dumps({
  "version": 2,
  "goal": sys.argv[1],
  "mode": "pipeline",
  "autonomy": "semi",
  "terminal": None,
  "terminal_reason": None,
  "current_stage": "plan",
  "iteration_count": 0,
  "stages": [
    {"id": "plan", "skill": "vd:plan", "done_when": "plan.md exists", "status": "pending"},
    {"id": "cook", "skill": "vd:cook", "done_when": "tests pass", "status": "pending"},
  ],
}))
PY
}

G1="${WORKDIR}/g1"
sample_state "first goal" | bash "$UPDATE" --init --goal-dir "$G1" >/dev/null
assert "init writes state" $? 0
test -f "${G1}/state.json"
assert "init created file" $? 0

python3 -c "import json; s=json.load(open('${G1}/state.json')); assert s['version']==2; assert s['created_at']"
assert "init version 2 + created_at" $? 0

# missing --goal-dir
set +e
bash "$UPDATE" --init </dev/null >/dev/null 2>&1
assert "init without --goal-dir" $? 2
set -e

# invalid version
Gbad="${WORKDIR}/bad-ver"
set +e
echo '{"version":1,"goal":"x","terminal":null,"stages":[{"id":"a","skill":"vd:plan","done_when":"x","status":"pending"}]}' \
  | bash "$UPDATE" --init --goal-dir "$Gbad" >/dev/null 2>&1
assert "init rejects version 1" $? 4
set -e

# invalid terminal
set +e
echo '{"version":2,"goal":"x","terminal":"nope","stages":[{"id":"a","skill":"vd:plan","done_when":"x","status":"pending"}]}' \
  | bash "$UPDATE" --init --goal-dir "${WORKDIR}/bad-term" >/dev/null 2>&1
assert "init rejects bad terminal" $? 4
set -e

# missing stage field
set +e
echo '{"version":2,"goal":"x","terminal":null,"stages":[{"id":"a","skill":"vd:plan","status":"pending"}]}' \
  | bash "$UPDATE" --init --goal-dir "${WORKDIR}/bad-stage" >/dev/null 2>&1
assert "init rejects stage missing done_when" $? 4
set -e

# bad stage status
set +e
echo '{"version":2,"goal":"x","terminal":null,"stages":[{"id":"a","skill":"vd:plan","done_when":"x","status":"later"}]}' \
  | bash "$UPDATE" --init --goal-dir "${WORKDIR}/bad-st" >/dev/null 2>&1
assert "init rejects bad stage status" $? 4
set -e

# unknown current_stage
set +e
echo '{"version":2,"goal":"x","terminal":null,"current_stage":"nope","stages":[{"id":"a","skill":"vd:plan","done_when":"x","status":"pending"}]}' \
  | bash "$UPDATE" --init --goal-dir "${WORKDIR}/bad-cur" >/dev/null 2>&1
assert "init rejects unknown current_stage" $? 4
set -e

# patch updates
echo '{"iteration_count": 3}' | bash "$UPDATE" --goal-dir "$G1" >/dev/null
python3 -c "import json; assert json.load(open('${G1}/state.json'))['iteration_count']==3"
assert "patch iteration_count" $? 0

# replace stages
echo '{"stages":[{"id":"plan","skill":"vd:plan","done_when":"plan.md exists","status":"done"},{"id":"cook","skill":"vd:cook","done_when":"tests pass","status":"in_progress"}],"current_stage":"cook"}' \
  | bash "$UPDATE" --goal-dir "$G1" >/dev/null
python3 -c "import json; s=json.load(open('${G1}/state.json')); assert s['stages'][0]['status']=='done'; assert s['current_stage']=='cook'"
assert "patch replaces stages" $? 0

# patch missing file
set +e
echo '{}' | bash "$UPDATE" --goal-dir "${WORKDIR}/missing" >/dev/null 2>&1
assert "patch missing file" $? 2
set -e

# crashed prior write
touch "${G1}/state.json.tmp"
set +e
echo '{}' | bash "$UPDATE" --goal-dir "$G1" >/dev/null 2>&1
assert "tmp crash guard" $? 3
set -e
rm -f "${G1}/state.json.tmp"

# status --goal-dir in-progress
set +e
out="$(bash "$STATUS" --goal-dir "$G1" 2>&1)"
rc=$?
set -e
assert "status in-progress exit" "$rc" 3
assert_grep "status shows cook as resume" "$out" "Resume:"
assert_grep "status shows in-progress cook" "$out" "cook"

# skipped stages are not resume targets
echo '{"stages":[{"id":"plan","skill":"vd:plan","done_when":"x","status":"skipped"},{"id":"cook","skill":"vd:cook","done_when":"x","status":"pending"}],"current_stage":"cook"}' \
  | bash "$UPDATE" --goal-dir "$G1" >/dev/null
out="$(bash "$STATUS" --goal-dir "$G1" 2>&1 || true)"
assert_grep "resume skips skipped stages" "$out" "Resume:      cook"

# terminal exits
echo '{"terminal":"done"}' | bash "$UPDATE" --goal-dir "$G1" >/dev/null
set +e
bash "$STATUS" --goal-dir "$G1" >/dev/null
assert "status done exit" $? 0
set -e

echo '{"terminal":"blocked","terminal_reason":"tests red"}' | bash "$UPDATE" --goal-dir "$G1" >/dev/null
set +e
out="$(bash "$STATUS" --goal-dir "$G1" 2>&1)"
rc=$?
set -e
assert "status blocked exit" "$rc" 1
assert_grep "status blocked reason" "$out" "tests red"

echo '{"terminal":"abandoned","terminal_reason":"stop"}' | bash "$UPDATE" --goal-dir "$G1" >/dev/null
set +e
bash "$STATUS" --goal-dir "$G1" >/dev/null
assert "status abandoned exit" $? 2
set -e

# kill refuse overwrite
set +e
out="$(bash "$KILL" --goal-dir "$G1" --reason "again" 2>&1)"
rc=$?
set -e
assert "kill refuses terminal" "$rc" 3
assert_grep "kill already_terminal json" "$out" "already_terminal"

# reopen + kill
echo '{"terminal":null,"terminal_reason":null}' | bash "$UPDATE" --goal-dir "$G1" >/dev/null
out="$(bash "$KILL" --goal-dir "$G1" --reason "user stop")"
assert "kill abandons" $? 0
assert_grep "kill abandoned json" "$out" '"abandoned": true'
python3 -c "import json; s=json.load(open('${G1}/state.json')); assert s['terminal']=='abandoned'; assert s['terminal_reason']=='user stop'"
assert "kill wrote reason" $? 0

# multi-goal list-and-pick
export VD_STATE_PATH="${WORKDIR}/store"
mkdir -p "$VD_STATE_PATH"
G2="${VD_STATE_PATH}/alpha"
G3="${VD_STATE_PATH}/beta"
sample_state "alpha" | bash "$UPDATE" --init --goal-dir "$G2" >/dev/null
sample_state "beta" | bash "$UPDATE" --init --goal-dir "$G3" >/dev/null

set +e
out="$(bash "$STATUS" 2>&1)"
rc=$?
set -e
assert "status multiple in-progress exit 6" "$rc" 6
assert_grep "status lists both" "$out" "alpha"

set +e
out="$(bash "$STATUS" --all 2>&1)"
rc=$?
set -e
assert "status --all with in-progress" "$rc" 0
assert_grep "status --all mentions count" "$out" "in-progress"

# single in-progress auto-select
echo '{"terminal":"done"}' | bash "$UPDATE" --goal-dir "$G3" >/dev/null
set +e
out="$(bash "$STATUS" 2>&1)"
rc=$?
set -e
assert "status single in-progress exit" "$rc" 3
assert_grep "status single shows alpha" "$out" "alpha"

# none in-progress
echo '{"terminal":"done"}' | bash "$UPDATE" --goal-dir "$G2" >/dev/null
set +e
out="$(bash "$STATUS" 2>&1)"
rc=$?
set -e
assert "status none in-progress" "$rc" 4
assert_grep "status none message" "$out" "no in-progress goal"

# kill default reason
G4="${VD_STATE_PATH}/gamma"
sample_state "gamma" | bash "$UPDATE" --init --goal-dir "$G4" >/dev/null
out="$(bash "$KILL" --goal-dir "$G4")"
assert "kill default reason" $? 0
python3 -c "import json; assert json.load(open('${G4}/state.json'))['terminal_reason']=='user-requested kill'"
assert "kill default reason stored" $? 0

echo
echo "summary: pass=${pass} fail=${fail}"
[ "$fail" -eq 0 ]
