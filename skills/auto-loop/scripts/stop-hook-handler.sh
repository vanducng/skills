#!/usr/bin/env bash
# stop-hook-handler.sh — Claude Code Stop hook entrypoint.
#
# Reads .auto-loop/heartbeat.json + goal-state.json. Decides whether to:
#   (a) re-feed a next-iteration prompt (loop continues),
#   (b) gracefully drain (cap reached),
#   (c) run completion gate on `achieved` (phase 4),
#   (d) exit silently (loop terminates).
#
# Stop-hook protocol: emit JSON `{"decision": "block", "reason": "<prompt>"}` on stdout
# to instruct Claude Code to re-feed; emit `{}` (empty object) to allow the session
# to end. Any other `decision` value triggers a JSON validation error in Claude Code.
# `stop_hook_active=true` in the input payload means we're already inside a re-feed
# chain — don't block again, or we infinite-loop.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

# Read stop-hook stdin payload (Claude Code injects JSON here). Capture both
# stop_hook_active (anti-infinite-loop guard) and any session metadata.
hook_payload=""
if [[ ! -t 0 ]]; then
  hook_payload=$(cat || true)
fi
stop_hook_active=$(printf '%s' "$hook_payload" | jq -r '.stop_hook_active // false' 2>/dev/null || echo "false")

# Resolve workspace from the working-tree root (Claude Code runs hooks at the
# workspace root; the worktree itself when inside one — keeps the cache tree-local).
ws="${VD_AUTOLOOP_WORKSPACE:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
state_dir="$ws/.auto-loop"
heartbeat="$state_dir/heartbeat.json"
state_file="$state_dir/goal-state.json"
gate_log="$state_dir/gate-history.jsonl"

# --- helpers ---
log_gate() {
  # log_gate <iter> <verifier> <audit> <decision>
  local iter="$1" verifier="$2" audit="$3" decision="$4"
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  jq -nc \
    --arg t "$now" \
    --argjson i "${iter:-0}" \
    --arg v "$verifier" \
    --arg a "$audit" \
    --arg d "$decision" \
    '{at:$t, iter:$i, verifier:$v, audit:$a, decision:$d}' >> "$gate_log"
}

emit_block() {
  # emit_block <prompt-string> — instruct Claude Code to re-feed.
  local prompt="$1"
  jq -nc --arg r "$prompt" '{decision: "block", reason: $r}'
}

emit_allow_stop() {
  # emit_allow_stop — let session end. Empty JSON object is the documented
  # "no-op" shape; any unknown `decision` value is rejected by Claude Code.
  printf '{}\n'
}

# --- 0. Anti-infinite-loop guard ---
# If Claude Code injected stop_hook_active=true, we're already mid-block-chain.
# Do NOT block again or we'll runaway. Allow stop and let dispatch decide if the
# loop should continue via a fresh invocation.
if [[ "$stop_hook_active" == "true" ]]; then
  emit_allow_stop
  exit 0
fi

# --- 1. Heartbeat sanity ---
if [[ ! -f "$heartbeat" ]]; then
  emit_allow_stop
  exit 0
fi

pid=$(jq -r '.pid // empty' "$heartbeat" 2>/dev/null || true)
if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
  # Stale or dead PID → purge and let session end.
  rm -f "$heartbeat"
  emit_allow_stop
  exit 0
fi

# --- 2. State file ---
if [[ ! -f "$state_file" ]]; then
  # No state yet → assume pursuing.
  current_status="pursuing"
  iter=0
  next_action="state file missing; first iteration"
  goal=$(jq -r '.goal_text // ""' "$heartbeat")
else
  current_status=$(jq -r '.status // "pursuing"' "$state_file")
  iter=$(jq -r '.iteration // 0' "$state_file")
  next_action=$(jq -r '.next_action // ""' "$state_file")
  goal=$(jq -r '.goal_text // ""' "$heartbeat")
fi

max_iter=$(jq -r '.max_iterations // 40' "$heartbeat")
verify_cmd=$(jq -r '.verify // ""' "$heartbeat")
allow=$(jq -r '.allow // ""' "$heartbeat")
deny=$(jq -r '.deny // ""' "$heartbeat")
max_wallclock=$(jq -r '.max_wallclock // "4h"' "$heartbeat")
started_at=$(jq -r '.started_at // ""' "$heartbeat")

# --- 3. Caps check (iter / tokens / wallclock) ---
# check-budget-caps.sh marks state=budget-limited on breach and emits a reason.
# On breach, render graceful-drain prompt for one final iteration (model commits
# and summarises), then allow stop.
caps_out=$(bash "$SCRIPT_DIR/check-budget-caps.sh" "$ws" 2>/dev/null || true)
caps_breach=$(printf '%s' "$caps_out" | jq -r '.reason // empty' 2>/dev/null || echo "")
if [[ -n "$caps_breach" ]]; then
  drain_template="$SKILL_DIR/templates/graceful-drain-prompt.md"
  drain_prompt=$(awk -v reason="$caps_breach" \
                     -v goal="$goal" \
                     -v iter="$iter" \
                     -v status="$current_status" \
                     -v elapsed="${elapsed_sec:-0}s" \
                     -v tokens="$(jq -r '.tokens_used // 0' "$state_file" 2>/dev/null)" \
                     '{
                       gsub(/\{REASON\}/, reason)
                       gsub(/\{GOAL\}/, goal)
                       gsub(/\{ITERATION\}/, iter)
                       gsub(/\{STATUS\}/, status)
                       gsub(/\{ELAPSED\}/, elapsed)
                       gsub(/\{TOKENS_USED\}/, tokens)
                       print
                     }' "$drain_template")
  log_gate "$iter" "not-run" "not-run" "drain:$caps_breach"
  emit_block "$drain_prompt"
  exit 0
fi

# --- 4. Status-based dispatch ---
case "$current_status" in
  cancelled)
    log_gate "$iter" "not-run" "not-run" "cancelled"
    emit_allow_stop
    exit 0
    ;;
  achieved)
    # Phase 4 wires completion-gate here.
    gate="$SCRIPT_DIR/check-completion-gate.sh"
    if [[ -x "$gate" ]]; then
      if bash "$gate" "$iter" "$verify_cmd" "$ws" >&2; then
        log_gate "$iter" "pass" "achieved" "achieved-final"
        emit_allow_stop
        exit 0
      else
        # Gate failed — re-read state, fall through to re-feed.
        current_status=$(jq -r '.status // "unmet"' "$state_file")
        next_action=$(jq -r '.next_action // ""' "$state_file")
      fi
    else
      # Phase-3 only fallback: trust the model, but log it.
      log_gate "$iter" "not-run" "not-run" "achieved-pre-verify"
      emit_allow_stop
      exit 0
    fi
    ;;
esac

# --- 5. Increment iter, recompute diff signature, write state ---
new_iter=$((iter + 1))
diff_sig=$(git -C "$ws" diff --stat 2>/dev/null | sha256sum | awk '{print $1}' || echo "")
now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [[ -f "$state_file" ]]; then
  updated=$(jq --argjson i "$new_iter" \
                --arg lu "$now" \
                --arg ds "$diff_sig" \
                '.iteration = $i | .last_update = $lu | .last_diff_signature = $ds' \
                "$state_file")
  bash "$SCRIPT_DIR/state-rw.sh" write "$state_file" "$updated" 2>/dev/null || true
fi

# --- 5a. Drift watchdog (advisory; may set status=blocked) ---
drift_out=$(bash "$SCRIPT_DIR/drift-watchdog.sh" "$ws" 2>/dev/null || echo '{"action":"none"}')
drift_action=$(printf '%s' "$drift_out" | jq -r '.action // "none"' 2>/dev/null || echo "none")
drift_note=$(printf '%s' "$drift_out" | jq -r '.note // ""' 2>/dev/null || echo "")
if [[ "$drift_action" == "blocked" ]]; then
  log_gate "$new_iter" "not-run" "blocked" "drift-blocked"
  emit_allow_stop
  exit 0
fi

# --- 5b. Context probe → phase-restart marker ---
restart_pct=$(jq -r '.restart_at_context_pct // 70' "$heartbeat" 2>/dev/null || echo 70)
ctx_out=$(bash "$SCRIPT_DIR/probe-context-pct.sh" 2>/dev/null || echo '{"pct":-1,"source":"unknown"}')
ctx_pct=$(printf '%s' "$ctx_out" | jq -r '.pct // -1' 2>/dev/null || echo -1)
if [[ "$ctx_pct" -ge 0 && "$ctx_pct" -ge "$restart_pct" ]]; then
  # Write compaction summary + marker; outer wrapper handles respawn.
  bash "$SCRIPT_DIR/restart-fresh-session.sh" "$ws" >/dev/null 2>&1 || true
  log_gate "$new_iter" "not-run" "not-run" "restart-needed"
  emit_allow_stop
  exit 0
fi

# --- 6. Render next-iter prompt ---
template="$SKILL_DIR/templates/next-iteration-prompt.md"
elapsed_sec=0
if [[ -n "$started_at" ]]; then
  s_epoch=$(date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$started_at" "+%s" 2>/dev/null || \
            date -u -d "$started_at" "+%s" 2>/dev/null || echo 0)
  now_epoch=$(date -u +"%s")
  elapsed_sec=$((now_epoch - s_epoch))
fi
elapsed_human=$(printf '%dh%dm' $((elapsed_sec/3600)) $(((elapsed_sec%3600)/60)))

pressure_note=""
if [[ "$max_iter" -gt 0 ]]; then
  pct=$(( (iter * 100) / max_iter ))
  if   [[ "$pct" -ge 90 ]]; then pressure_note="WARNING: 90% iteration budget consumed. Document blockers; do not start new work."
  elif [[ "$pct" -ge 75 ]]; then pressure_note="CAUTION: 75% iteration budget consumed. Prioritize finishing over polish."
  fi
fi
# Append drift watchdog advisory (thrashing) to pressure_note
if [[ "$drift_action" == "thrashing" && -n "$drift_note" ]]; then
  pressure_note="${pressure_note}${pressure_note:+ }DRIFT: $drift_note. Try a structurally different approach."
fi

verifier_result=$(jq -r '.verifier_result // "not-run"' "$state_file" 2>/dev/null || echo "not-run")
audit_vote=$(jq -r '.audit_vote // "not-run"' "$state_file" 2>/dev/null || echo "not-run")
blockers_str=$(jq -r '(.blockers // []) | join("; ")' "$state_file" 2>/dev/null || echo "")

prompt=$(awk -v iter="$iter" \
             -v iter_next="$new_iter" \
             -v max_iter="$max_iter" \
             -v goal="$goal" \
             -v status="$current_status" \
             -v na="$next_action" \
             -v blockers="$blockers_str" \
             -v vr="$verifier_result" \
             -v av="$audit_vote" \
             -v elapsed="$elapsed_human" \
             -v maxwall="$max_wallclock" \
             -v pressure="$pressure_note" \
             -v verify="$verify_cmd" \
             -v allow="$allow" \
             -v deny="$deny" \
             -v skill="$SKILL_DIR" '
{
  gsub(/\{ITERATION\}/, iter)
  gsub(/\{ITERATION_NEXT\}/, iter_next)
  gsub(/\{MAX_ITERATIONS\}/, max_iter)
  gsub(/\{GOAL\}/, goal)
  gsub(/\{STATUS\}/, status)
  gsub(/\{NEXT_ACTION\}/, na)
  gsub(/\{BLOCKERS\}/, blockers)
  gsub(/\{VERIFIER_RESULT\}/, vr)
  gsub(/\{AUDIT_VOTE\}/, av)
  gsub(/\{ELAPSED\}/, elapsed)
  gsub(/\{MAX_WALLCLOCK\}/, maxwall)
  gsub(/\{PRESSURE_NOTE\}/, pressure)
  gsub(/\{VERIFY\}/, verify)
  gsub(/\{ALLOW\}/, allow)
  gsub(/\{DENY\}/, deny)
  gsub(/\{SKILL_DIR\}/, skill)
  print
}' "$template")

log_gate "$iter" "$verifier_result" "$audit_vote" "re-feed"
emit_block "$prompt"
exit 0
