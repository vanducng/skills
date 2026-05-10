#!/usr/bin/env bash
# run-verifier.sh — execute the user-supplied verify command twice.
#
# Returns one of: pass | fail | flaky on stdout. Captures stdout+stderr to
# .auto-loop/verifier-{iter}.log (rotates, keeps last 20). Exit code:
#   0 = pass, 1 = fail, 2 = flaky, 3 = usage error.
#
# Usage: run-verifier.sh <iter> <verify-cmd> <workspace>

set -uo pipefail

iter="${1:?iter required}"
verify_cmd="${2:?verify-cmd required}"
ws="${3:?workspace required}"

cd "$ws"

state_dir=".auto-loop"
mkdir -p "$state_dir"

log="$state_dir/verifier-${iter}.log"

# Rotate: keep last 20
ls -1 "$state_dir"/verifier-*.log 2>/dev/null | sort | head -n -20 | xargs -I{} rm -f {} 2>/dev/null || true

# Run 1
echo "===== run 1 of 2 (iter=$iter) =====" > "$log"
bash -c "$verify_cmd" >> "$log" 2>&1
rc1=$?
echo "exit_code=$rc1" >> "$log"

# Run 2
echo "===== run 2 of 2 (iter=$iter) =====" >> "$log"
bash -c "$verify_cmd" >> "$log" 2>&1
rc2=$?
echo "exit_code=$rc2" >> "$log"

if [[ "$rc1" -eq 0 && "$rc2" -eq 0 ]]; then
  echo "pass"
  exit 0
fi
if [[ "$rc1" -ne 0 && "$rc2" -ne 0 ]]; then
  echo "fail"
  exit 1
fi
echo "flaky"
exit 2
