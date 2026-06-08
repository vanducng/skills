#!/usr/bin/env bash
# resolve-workflow.sh — dry-run resolver for a goal-dir.
#
# Given plans/goals/{slug}/goal.yaml, looks up the matching project profile
# via lookup-profile.sh, merges the profile's action sequence with any
# goal.yaml.actions overrides, and prints the resolved workflow in human-
# readable form.
#
# Stdout: text report (action sequence + verifier per action + gate hints).
# Exit: 0 on success, non-zero on resolution failures (missing profile,
#       unknown action, etc.).
#
# Usage: resolve-workflow.sh <goal-dir>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
PROJECTS_DIR="${SKILL_DIR}/projects"
VOCAB_DIR="${SKILL_DIR}/references"

# ── Args ──────────────────────────────────────────────────────────────────────

if [ $# -lt 1 ] || [ -z "${1:-}" ]; then
  echo "usage: resolve-workflow.sh <goal-dir>" >&2
  exit 2
fi
GOAL_DIR="$1"
if [ ! -f "${GOAL_DIR}/goal.yaml" ]; then
  echo "resolve-workflow.sh: ${GOAL_DIR}/goal.yaml not found" >&2
  exit 2
fi

# ── Python helper to parse YAML/TOML (uses ~/.claude/skills/.venv) ────────────
# The venv has yaml + tomllib (Python 3.11+). Fall back to system python3 if
# the venv is missing.

PYBIN="${HOME}/.claude/skills/.venv/bin/python3"
if [ ! -x "$PYBIN" ]; then PYBIN="$(command -v python3)"; fi
if [ -z "$PYBIN" ]; then
  echo "resolve-workflow.sh: python3 not found (needed for YAML/TOML parsing)" >&2
  exit 4
fi

# ── Extract goal.yaml fields ──────────────────────────────────────────────────

read_goal() {
  "$PYBIN" - "$GOAL_DIR/goal.yaml" <<'PY'
import sys, yaml, shlex
g = yaml.safe_load(open(sys.argv[1]))
project = g.get('project', {}) or {}
target  = g.get('target', {}) or {}
def q(v): return shlex.quote(str(v) if v is not None else "")
print(f"slug={q(g.get('slug',''))}")
print(f"short_goal={q(g.get('short_goal',''))}")
print(f"remote_url={q(project.get('remote_url',''))}")
print(f"target_kind={q(target.get('kind',''))}")
print(f"autonomy={q(g.get('autonomy','semi'))}")
print(f"risk_tier={q(g.get('risk_tier',''))}")
print(f"actions_override={q(','.join(g.get('actions') or []))}")
print(f"target_verifiers_count={q(len(target.get('verifiers') or []))}")
PY
}

eval "$(read_goal | sed 's/^/G_/')"

# ── Resolve profile ───────────────────────────────────────────────────────────

PROFILE_PATH="$(bash "${SCRIPT_DIR}/lookup-profile.sh" --remote-url "$G_remote_url")"
PROFILE_BASE="$(basename "$PROFILE_PATH")"

# ── Read profile fields via Python tomllib ────────────────────────────────────

read_profile() {
  "$PYBIN" - "$PROFILE_PATH" "$G_target_kind" <<'PY'
import sys, tomllib, shlex
prof = tomllib.load(open(sys.argv[1], 'rb'))
kind = sys.argv[2]
seq_key = {
    'local':    'default_sequence_local',
    'pr-only':  'default_sequence_pr_only',
    'cluster':  'default_sequence_cluster',
}.get(kind, 'default_sequence_pr_only')
actions = prof.get('actions', {})
def q(v): return shlex.quote(str(v) if v is not None else "")
print(f"P_name={q(prof.get('project',{}).get('name',''))}")
print(f"P_ship_mode={q(prof.get('project',{}).get('ship_mode',''))}")
print(f"P_seq={q(','.join(actions.get(seq_key, [])))}")
print(f"P_test_cmd={q(prof.get('verify',{}).get('test_cmd',''))}")
PY
}

eval "$(read_profile)"

# ── Merge actions: goal override wins; else profile's default-for-kind ────────

# Merge rule:
#   - goal.yaml.actions is the PREFIX (set by intake's action-shape question).
#   - profile.default_sequence_<kind> is the BASE.
#   - Dedup: skip base entries already present in the prefix.
if [ -n "$G_actions_override" ]; then
  RESOLVED_ACTIONS="$("$PYBIN" - <<PY
import shlex
prefix = "$G_actions_override".split(',')
base = "$P_seq".split(',')
seen = set()
out = []
for a in prefix + base:
    a = a.strip()
    if not a or a in seen: continue
    seen.add(a)
    out.append(a)
print(','.join(out))
PY
)"
  ACTIONS_SOURCE="goal.yaml.actions (prefix) + profile (base)"
else
  RESOLVED_ACTIONS="$P_seq"
  ACTIONS_SOURCE="profile.default_sequence_$(echo "$G_target_kind" | tr '-' '_')"
fi

# Auto-prepend plan_audit when risk_tier=high and not already present
if [ "$G_risk_tier" = "high" ]; then
  case ",$RESOLVED_ACTIONS," in
    *,plan_audit,*) ;;
    *)
      # Insert plan_audit after the first "plan" action.
      RESOLVED_ACTIONS="$(printf '%s' "$RESOLVED_ACTIONS" | sed -E 's/(^|,)plan(,|$)/\1plan,plan_audit\2/')"
      ;;
  esac
fi

# ── Read action-vocab.yaml for per-action verifier + gate_default lookups ─────

action_meta() {
  local action="$1"
  "$PYBIN" - "${VOCAB_DIR}/action-vocab.yaml" "$action" <<'PY'
import sys, yaml, shlex
v = yaml.safe_load(open(sys.argv[1]))
action = sys.argv[2]
a = v.get('actions', {}).get(action)
if not a:
    print("UNKNOWN")
    sys.exit(0)
disp = a.get('dispatch','')
verifier = a.get('verifier')
verifier_str = '-'
if isinstance(verifier, dict):
    if 'from_target_verifiers' in verifier:
        verifier_str = f"target.verifiers({verifier['from_target_verifiers']})"
    elif 'type' in verifier:
        verifier_str = verifier['type']
gates = a.get('gate_default') or []
def q(v): return shlex.quote(str(v) if v is not None else "")
print(f"dispatch={q(disp)}")
print(f"verifier={q(verifier_str)}")
print(f"gate_default={q(','.join(gates))}")
print(f"parallel_with={q(','.join(a.get('parallel_with') or []))}")
print(f"delegated_to={q(a.get('delegated_to') or '-')}")
PY
}

# ── Print resolved workflow report ────────────────────────────────────────────

echo "# Resolved workflow"
echo
echo "**Goal:** ${G_short_goal}"
echo "**Slug:** ${G_slug}"
echo "**Profile:** ${PROFILE_BASE} (matched on ${G_remote_url})"
echo "**Target kind:** ${G_target_kind}"
echo "**Autonomy:** ${G_autonomy}"
echo "**Risk tier:** ${G_risk_tier:-(unset)}"
echo "**Action source:** ${ACTIONS_SOURCE}"
echo "**Ship mode:** ${P_ship_mode}"
echo "**Test cmd (per profile):** ${P_test_cmd:-(none)}"
echo "**Workflow-level verifiers (target.verifiers):** ${G_target_verifiers_count}"
echo
echo "## Action sequence"
echo

# Walk the comma-separated sequence
IFS=',' read -r -a ACTIONS_ARR <<< "$RESOLVED_ACTIONS"
i=0
exit_code=0
for action in "${ACTIONS_ARR[@]}"; do
  i=$((i + 1))
  meta="$(action_meta "$action")"
  if echo "$meta" | head -1 | grep -q UNKNOWN; then
    printf '%2d. %-22s ❌ UNKNOWN ACTION — not in action-vocab.yaml\n' "$i" "$action"
    exit_code=5
    continue
  fi
  eval "$(echo "$meta" | sed 's/^/M_/')"
  # Gate hint: does this action gate under current autonomy?
  gate_hint="-"
  if echo ",$M_gate_default," | grep -q ",${G_autonomy},"; then
    gate_hint="gate"
  fi
  if [ "$G_autonomy" = "manual" ]; then gate_hint="gate"; fi
  if [ "$G_autonomy" = "auto" ]; then gate_hint="-"; fi
  delegate_hint=""
  [ "$M_delegated_to" != "-" ] && delegate_hint=" [delegate → ${M_delegated_to}]"

  printf '%2d. %-22s dispatch=%-32s verifier=%-30s %s%s\n' \
    "$i" "$action" "$M_dispatch" "$M_verifier" "$gate_hint" "$delegate_hint"
done

echo
echo "(legend: gate = user-confirmed in current autonomy mode '${G_autonomy}'; '-' = auto-progress)"

exit $exit_code
