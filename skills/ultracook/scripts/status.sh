#!/usr/bin/env bash
# status.sh — print a one-screen status summary for a ultracook goal.
#
# Usage:
#   status.sh [--goal-dir <dir>]
#
# If --goal-dir omitted, auto-detects by scanning the configured state base,
# user-level default state, and legacy repo-local plans/goals/*/. If none found,
# prints "no in-progress goal" and exits 4.
#
# Exit codes (scriptable):
#   0 = terminal=done
#   1 = terminal=blocked
#   2 = terminal=abandoned
#   3 = in-progress (terminal=null)
#   4 = no goal found
#   5 = error reading state

set -uo pipefail

GOAL_DIR=""
ALL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --goal-dir)   GOAL_DIR="${2:-}"; shift 2 ;;
    --all|--list) ALL=1; shift ;;
    --help|-h)    echo "usage: status.sh [--goal-dir <dir>] [--all|--list]"; exit 0 ;;
    *) echo "status.sh: unknown arg: $1" >&2; exit 5 ;;
  esac
done

PYBIN="${HOME}/.claude/skills/.venv/bin/python3"; [ -x "$PYBIN" ] || PYBIN="$(command -v python3)"

# Resolve state bases: $VD_STATE_PATH → <git-root>/.workbench/state (or legacy
# .work) → XDG user state. Legacy plans/goals is still included for read-only resume.
# Returns newline-separated list of glob patterns (may include both new + legacy).
_hash12() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | awk '{print substr($1, 1, 12)}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum | awk '{print substr($1, 1, 12)}'
  else
    cksum | awk '{print $1}'
  fi
}

_state_repo_id() {
  local root="$1"
  local source name hash
  source="$(git -C "$root" remote get-url origin 2>/dev/null || printf '%s' "$root")"
  name="$(printf '%s' "$source" | sed -E 's#\\#/#g; s#^.*[:/]##; s#[.]git$##')"
  if [ -z "$name" ]; then
    name="$(basename "$root")"
  fi
  name="$(printf '%s' "$name" \
    | tr '[:upper:]' '[:lower:]' \
    | LC_ALL=C sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')"
  if [ -z "$name" ]; then
    name="repo"
  fi
  hash="$(printf '%s' "$source" | _hash12)"
  echo "${name}-${hash}"
}

_state_globs() {
  if [ -n "${VD_STATE_PATH:-}" ]; then
    echo "${VD_STATE_PATH}/*/state.json"
  fi
  REPO_ROOT_S="$(git rev-parse --show-toplevel 2>/dev/null || echo '')"
  if [ -n "$REPO_ROOT_S" ] && [ -d "${REPO_ROOT_S}/.workbench" ]; then
    echo "${REPO_ROOT_S}/.workbench/state/*/state.json"
  elif [ -n "$REPO_ROOT_S" ] && [ -d "${REPO_ROOT_S}/.work" ]; then
    echo "${REPO_ROOT_S}/.work/state/*/state.json"
  fi
  if [ -n "$REPO_ROOT_S" ]; then
    echo "${XDG_STATE_HOME:-${HOME}/.local/state}/vd/ultracook/$(_state_repo_id "$REPO_ROOT_S")/goals/*/state.json"
    # Always include legacy so read-either works without writing new state there.
    echo "${REPO_ROOT_S}/plans/goals/*/state.json"
  else
    echo "plans/goals/*/state.json"
  fi
}

# --all / --list: enumerate every goal-dir (#66 multi-goal disambiguation).
# Exit 0 if any in-progress goal exists, else 4.
if [ "$ALL" -eq 1 ]; then
  mapfile -t _GLOBS < <(_state_globs)
  _UC_GLOBS="$(printf '%s\n' "${_GLOBS[@]}")" "$PYBIN" - <<'PY'
import os, json, glob, time

patterns = [l for l in os.environ.get("_UC_GLOBS", "").splitlines() if l.strip()]
seen, rows, inprog = set(), [], 0
for pat in patterns:
    for sj in sorted(glob.glob(pat)):
        gd = os.path.dirname(sj)
        if gd in seen:
            continue
        seen.add(gd)
        try: s = json.load(open(sj))
        except Exception: continue
        g = {}
        gy = os.path.join(gd, "goal.yaml")
        if os.path.exists(gy):
            try:
                import yaml; g = yaml.safe_load(open(gy)) or {}
            except Exception: g = {}
        term = s.get("terminal") or "in-progress"
        if term == "in-progress": inprog += 1
        last = (s.get("last_action_result") or {}).get("action", "-")
        age_d = (time.time() - os.path.getmtime(sj)) / 86400
        rows.append((os.path.basename(gd), g.get("slug", "?"), term,
                     f"{age_d:.1f}d", s.get("iteration_count", 0), last))
if not rows:
    print("no goals found"); raise SystemExit(4)
print(f"{'goal-dir':<46} {'state':<11} {'age':>6} {'iter':>4} last-action")
print("-" * 86)
for gd, slug, term, age, it, last in rows:
    print(f"{gd:<46} {term:<11} {age:>6} {it:>4} {last}")
print(f"\n{len(rows)} goal(s), {inprog} in-progress")
raise SystemExit(0 if inprog else 4)
PY
  exit $?
fi

# Auto-detect: most recent state.json with terminal=null, scanning both bases.
if [ -z "$GOAL_DIR" ]; then
  candidates=()
  mapfile -t _GLOBS < <(_state_globs)
  for pat in "${_GLOBS[@]}"; do
    # Expand glob manually (avoids issues when no match).
    for sj in $pat; do
      d="$(dirname "$sj")"
      [ -d "$d" ] || continue
      [ -f "$d/state.json" ] || continue
      candidates+=("$d")
    done
  done
  # Deduplicate (in case legacy and new-base resolve to same path).
  IFS=$'\n' candidates=($(printf '%s\n' "${candidates[@]}" | sort -u))
  if [ "${#candidates[@]}" -eq 0 ]; then
    echo "status.sh: no goal-dir found (checked: ${_GLOBS[*]})" >&2
    exit 4
  fi
  # Sort by name (timestamp-prefix → most recent last).
  IFS=$'\n' SORTED=($(sort <<< "${candidates[*]}"))
  GOAL_DIR="${SORTED[-1]}"
fi

[ -f "${GOAL_DIR}/state.json" ] || { echo "status.sh: ${GOAL_DIR}/state.json not found" >&2; exit 5; }
[ -f "${GOAL_DIR}/goal.yaml" ]   || { echo "status.sh: ${GOAL_DIR}/goal.yaml not found"   >&2; exit 5; }

PYBIN="${HOME}/.claude/skills/.venv/bin/python3"; [ -x "$PYBIN" ] || PYBIN="$(command -v python3)"

GOAL_DIR="$GOAL_DIR" "$PYBIN" - <<'PY'
import os, json, yaml
gd = os.environ["GOAL_DIR"]
s = json.load(open(os.path.join(gd, "state.json")))
g = yaml.safe_load(open(os.path.join(gd, "goal.yaml")))

terminal = s.get("terminal")
mode_label = {"done":"DONE","blocked":"BLOCKED","abandoned":"ABANDONED",None:"in-progress"}.get(terminal,"unknown")
last = s.get("last_action_result") or {}

print(f"Goal:        {g.get('short_goal','')}")
print(f"Slug:        {g.get('slug','')}")
print(f"Mode:        {g.get('autonomy','semi')}")
print(f"Status:      {mode_label}{' at ' + (s.get('current_action') or '(intake-complete)') if not terminal else ''}")
b  = g.get('budgets') or {}
bc = s.get('budgets_consumed') or {}
print(f"Iterations:  {s.get('iteration_count',0)} / {b.get('max_iterations','?')}")
print(f"Budget used: rebases {bc.get('rebases',0)}/{b.get('max_rebases','?')}, "
      f"ci-reruns {bc.get('ci_reruns',0)}/{b.get('max_ci_reruns','?')}, "
      f"tokens ~{bc.get('token_pct',0)}%")
if last:
    print(f"Last action: {last.get('action','?')} → "
          f"{'verifier_pass' if last.get('verifier_pass') else 'verifier_fail'} "
          f"({last.get('verifier_evidence','')[:80]})")
    print(f"Last journal: {last.get('journal_entry','')}")
if s.get('terminal_reason'):
    print(f"Terminal reason: {s.get('terminal_reason')}")
PY

# Exit code per terminal state.
T="$("$PYBIN" -c "import json; print(json.load(open('${GOAL_DIR}/state.json')).get('terminal') or 'null')")"
case "$T" in
  done)      exit 0 ;;
  blocked)   exit 1 ;;
  abandoned) exit 2 ;;
  null)      exit 3 ;;
  *)         exit 5 ;;
esac
