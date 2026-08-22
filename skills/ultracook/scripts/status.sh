#!/usr/bin/env bash
# status.sh - print ultracook goal status (schema v2).
#
# Usage:
#   status.sh [--goal-dir <dir>] [--all]
#
# With no --goal-dir:
#   0 in-progress  -> "no in-progress goal" (exit 4)
#   1 in-progress  -> print that goal
#   N in-progress  -> list them and exit 6 (caller must pick; no silent newest-wins)
#
# --all lists every known goal-dir (in-progress and terminal).
#
# Exit:
#   0 done · 1 blocked · 2 abandoned · 3 in-progress · 4 none · 5 error · 6 pick required
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
. "${SCRIPT_DIR}/lib.sh"

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

PYBIN="$(_uc_python)"

_collect_state_files() {
  _uc_state_globs | while IFS= read -r pat; do
    [ -n "$pat" ] || continue
    # shellcheck disable=SC2086
    for sj in $pat; do
      [ -f "$sj" ] || continue
      printf '%s\n' "$sj"
    done
  done | sort -u
}

_print_list() {
  local filter_inprog="$1"
  FILES="${2:-}" FILTER="$filter_inprog" "$PYBIN" - <<'PY'
import json, os, sys, time

filter_inprog = os.environ.get("FILTER") == "inprog"
paths = [l.strip() for l in os.environ.get("FILES", "").splitlines() if l.strip()]
seen, rows = set(), []
inprog = 0
for sj in paths:
    gd = os.path.dirname(sj)
    if gd in seen:
        continue
    seen.add(gd)
    try:
        s = json.load(open(sj))
    except Exception:
        continue
    term = s.get("terminal")
    if term is None:
        inprog += 1
        term_label = "in-progress"
    else:
        term_label = str(term)
    if filter_inprog and term is not None:
        continue
    stages = s.get("stages") or []
    nxt = next((st["id"] for st in stages if st.get("status") not in ("done", "skipped")), "-")
    age_d = (time.time() - os.path.getmtime(sj)) / 86400
    rows.append((os.path.basename(gd), s.get("goal", "?"), term_label,
                 f"{age_d:.1f}d", s.get("iteration_count", 0), nxt, gd))

if not rows:
    print("no goals found")
    sys.exit(4)

print(f"{'goal-dir':<40} {'state':<11} {'age':>6} {'iter':>4} next")
print("-" * 80)
for slug, goal, term, age, it, nxt, _gd in rows:
    print(f"{slug:<40} {term:<11} {age:>6} {it:>4} {nxt}")
print(f"\n{len(rows)} goal(s), {inprog} in-progress")
for _slug, _goal, _term, _age, _it, _nxt, gd in rows:
    print(f"  {gd}")
sys.exit(0 if (inprog or not filter_inprog) else 4)
PY
}

_print_one() {
  local gd="$1"
  [ -f "${gd}/state.json" ] || { echo "status.sh: ${gd}/state.json not found" >&2; exit 5; }
  GOAL_DIR="$gd" "$PYBIN" - <<'PY'
import json, os, sys
gd = os.environ["GOAL_DIR"]
s = json.load(open(os.path.join(gd, "state.json")))
term = s.get("terminal")
label = {None: "in-progress", "done": "DONE", "blocked": "BLOCKED", "abandoned": "ABANDONED"}.get(term, str(term))
print(f"Goal:        {s.get('goal', '')}")
print(f"Dir:         {gd}")
print(f"Mode:        {s.get('mode', '-')}/{s.get('autonomy', 'semi')}")
print(f"Status:      {label}")
print(f"Iterations:  {s.get('iteration_count', 0)}")
if s.get("terminal_reason"):
    print(f"Reason:      {s.get('terminal_reason')}")
print("Stages:")
resume = None
for st in s.get("stages") or []:
    mark = {"done": "x", "skipped": "-", "in_progress": ">", "pending": " "}.get(st.get("status"), "?")
    print(f"  [{mark}] {st.get('id')}  {st.get('skill')}  ({st.get('status')})")
    print(f"      done_when: {st.get('done_when')}")
    if st.get("evidence"):
        print(f"      evidence:  {st.get('evidence')}")
    if resume is None and st.get("status") not in ("done", "skipped"):
        resume = st.get("id")
if term is None:
    print(f"Resume:      {resume or '(all stages done - mark terminal)'}")
PY
  local t
  t="$("$PYBIN" -c "import json; print(json.load(open('${gd}/state.json')).get('terminal') or 'null')")"
  case "$t" in
    done)      exit 0 ;;
    blocked)   exit 1 ;;
    abandoned) exit 2 ;;
    null)      exit 3 ;;
    *)         exit 5 ;;
  esac
}

if [ "$ALL" -eq 1 ]; then
  files="$(_collect_state_files || true)"
  if [ -z "$files" ]; then
    echo "no goals found"
    exit 4
  fi
  _print_list all "$files"
  exit $?
fi

if [ -n "$GOAL_DIR" ]; then
  _print_one "$GOAL_DIR"
fi

files="$(_collect_state_files || true)"
if [ -z "$files" ]; then
  echo "no in-progress goal"
  exit 4
fi

inprog="$(FILES="$files" "$PYBIN" - <<'PY'
import json, os
for sj in os.environ.get("FILES", "").splitlines():
    sj = sj.strip()
    if not sj:
        continue
    try:
        s = json.load(open(sj))
    except Exception:
        continue
    if s.get("terminal") is None:
        print(sj)
PY
)"

count=0
if [ -n "$inprog" ]; then
  count="$(printf '%s\n' "$inprog" | grep -c . || true)"
fi

if [ "$count" -eq 0 ]; then
  echo "no in-progress goal"
  exit 4
fi

if [ "$count" -gt 1 ]; then
  echo "multiple in-progress goals - pick one with --goal-dir:"
  _print_list inprog "$inprog"
  exit 6
fi

_print_one "$(dirname "$inprog")"
