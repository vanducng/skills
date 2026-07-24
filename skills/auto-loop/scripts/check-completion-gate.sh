#!/usr/bin/env bash
# check-completion-gate.sh - two-vote gate. Run verifier 2x; if pass, spawn audit
# subagent. Both must vote `achieved` for the gate to open. Updates goal-state.json.
#
# Exit code:
#   0 = gate opened (terminal achieved)
#   1 = gate closed (loop continues with `unmet`)
#
# Usage: check-completion-gate.sh <iter> <verify-cmd> <workspace>

set -uo pipefail

iter="${1:?iter required}"
verify_cmd="${2:?verify-cmd required}"
ws="${3:?workspace required}"

cd "$ws"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_state-dir.sh"
state_file="$state_dir/goal-state.json"
gate_log="$state_dir/gate-history.jsonl"

now() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

write_state() {
  # write_state <status> <next_action> <verifier_result> <audit_vote>
  local status="$1" na="$2" vr="$3" av="$4"
  local current
  current=$(cat "$state_file")
  local updated
  updated=$(printf '%s' "$current" | jq \
    --arg s "$status" \
    --arg n "$na" \
    --arg vr "$vr" \
    --arg av "$av" \
    --arg lu "$(now)" \
    '.status = $s
     | .next_action = $n
     | .verifier_result = $vr
     | .audit_vote = $av
     | .last_update = $lu')
  bash "$SCRIPT_DIR/state-rw.sh" write "$state_file" "$updated"
}

log_gate() {
  local v="$1" a="$2" d="$3"
  jq -nc --arg t "$(now)" \
        --argjson i "$iter" \
        --arg v "$v" \
        --arg a "$a" \
        --arg d "$d" \
        '{at:$t, iter:$i, verifier:$v, audit:$a, decision:$d}' >> "$gate_log"
}

# --- 1. Verifier (2x) ---
verifier_out=$(bash "$SCRIPT_DIR/run-verifier.sh" "$iter" "$verify_cmd" "$ws" 2>/dev/null || true)
case "$verifier_out" in
  pass)  verifier_result="pass" ;;
  fail)  verifier_result="fail" ;;
  flaky) verifier_result="flaky" ;;
  *)     verifier_result="fail" ;;
esac

if [[ "$verifier_result" != "pass" ]]; then
  reason="verifier ${verifier_result}: see verifier-${iter}.log"
  write_state "unmet" "$reason" "$verifier_result" "not-run"
  log_gate "$verifier_result" "not-run" "unmet-verifier"
  exit 1
fi

# --- 2. Audit subagent ---
audit_json=$(bash "$SCRIPT_DIR/spawn-audit-subagent.sh" "$iter" "$verify_cmd" "$ws" 2>/dev/null || \
             echo '{"vote":"unmet","reason":"spawn failed","missing":[]}')
vote=$(printf '%s' "$audit_json" | jq -r '.vote')
audit_reason=$(printf '%s' "$audit_json" | jq -r '.reason // ""')
missing=$(printf '%s' "$audit_json" | jq -r '(.missing // []) | join(", ")')

case "$vote" in
  achieved)
    write_state "achieved" "two-vote gate passed" "pass" "achieved"
    log_gate "pass" "achieved" "achieved-final"
    exit 0
    ;;
  blocked)
    write_state "blocked" "audit voted blocked: $audit_reason" "pass" "blocked"
    log_gate "pass" "blocked" "blocked"
    exit 1
    ;;
  *)
    reason="audit said: ${audit_reason}"
    [[ -n "$missing" ]] && reason+="; missing: ${missing}"
    write_state "unmet" "$reason" "pass" "unmet"
    log_gate "pass" "unmet" "unmet-audit"
    exit 1
    ;;
esac
