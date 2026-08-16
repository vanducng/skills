#!/usr/bin/env bash
# status.sh - one-line-per-goal status from state.json files (schema v2).
#
# Usage:
#   status.sh <state-base>            (summarize every goal dir under the base)
#   status.sh <state-base>/<slug>     (detail for one goal, including stages)
#
# The caller resolves <state-base> per the SKILL.md rules:
#   $VD_STATE_PATH → <git-root>/.workbench/state → $XDG_STATE_HOME/vd/ultracook/<repo-id>/goals

set -euo pipefail

TARGET="${1:?usage: status.sh <state-base>[/<slug>]}"

render() {
  local dir="$1" detail="$2"
  [ -f "$dir/state.json" ] || return 0
  DETAIL="$detail" "$(command -v python3)" - "$dir" <<'PY'
import json, sys, os
d = sys.argv[1]
slug = os.path.basename(d.rstrip("/"))

def render_goal():
    with open(os.path.join(d, "state.json")) as f:
        s = json.load(f)
    if not isinstance(s, dict) or s.get("version") != 2:
        # Legacy v0.x goals share the state base but are not resumable (and kill.sh rejects them).
        v = s.get("version", "?") if isinstance(s, dict) else "?"
        print(f"{slug:32} legacy-v{v}    not resumable by ultracook v1 - finish with old tooling or delete the dir")
        return
    term = s.get("terminal") or "in-progress"
    stages = [st for st in s.get("stages", []) if isinstance(st, dict)]
    done = sum(1 for st in stages if st.get("status") == "done")
    cur = next((st.get("skill", "?") for st in stages if st.get("status") == "running"), None) \
       or next((st.get("skill", "?") for st in stages if st.get("status", "pending") == "pending"), "-")
    print(f"{slug:32} {term:12} stage {done}/{len(stages)} (next: {cur})  iter {s.get('iteration_count', 0)}  updated {s.get('updated_at', '?')}")
    if s.get("terminal_reason"):
        print(f"{'':32} reason: {s['terminal_reason']}")
    if os.environ.get("DETAIL") == "1":
        for st in stages:
            print(f"  {st.get('skill', '?'):14} {st.get('status', 'pending'):8} done-when: {st.get('done_when', '-')}")
            if st.get("evidence"):
                print(f"  {'':14} evidence: {st['evidence']}")

try:
    render_goal()
except Exception as e:
    # One corrupt/truncated/malformed state.json must not hide the other goals.
    print(f"{slug:32} unreadable   state.json invalid ({e.__class__.__name__}) - inspect or delete the dir")
PY
}

if [ -f "$TARGET/state.json" ]; then
  render "$TARGET" 1
elif [ -d "$TARGET" ]; then
  found=0
  for d in "$TARGET"/*/; do
    [ -f "$d/state.json" ] || continue
    render "$d" 0
    found=1
  done
  if [ "$found" -eq 0 ]; then echo "status.sh: no goals under $TARGET"; fi
else
  echo "status.sh: $TARGET not found" >&2
  exit 2
fi
