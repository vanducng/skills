#!/usr/bin/env bash
# delegate-to-auto-loop.sh — prepare a vd:auto-loop invocation for the given
# action. Does NOT actually call vd:auto-loop (that's the Skill tool, which
# only SKILL.md can invoke). Returns a JSON hint on stdout.
#
# Recursion guard: refuses if VD_AUTOLOOP_DEPTH > 0 (auto-loop's audit subagent
# must not recursively run pursue).
#
# Marker: writes {goal-dir}/.pursue/delegated-to-auto-loop.json so cross-
# session resume can detect mid-delegation state.
#
# Usage: delegate-to-auto-loop.sh --goal-dir <dir> --action <name> --iter <NNN>

set -uo pipefail

GOAL_DIR=""; ACTION=""; ITER="000"
while [ $# -gt 0 ]; do
  case "$1" in
    --goal-dir) GOAL_DIR="${2:-}"; shift 2 ;;
    --action)   ACTION="${2:-}"; shift 2 ;;
    --iter)     ITER="${2:-000}"; shift 2 ;;
    *) echo "delegate-to-auto-loop.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -z "$GOAL_DIR" ] && { echo "--goal-dir required" >&2; exit 2; }
[ -z "$ACTION" ]   && { echo "--action required"   >&2; exit 2; }

# Recursion guard.
if [ "${VD_AUTOLOOP_DEPTH:-0}" -gt 0 ]; then
  echo "delegate-to-auto-loop.sh: VD_AUTOLOOP_DEPTH=$VD_AUTOLOOP_DEPTH > 0 — refusing recursive pursue inside auto-loop audit subagent" >&2
  exit 4
fi

# Precondition: vd:auto-loop must be installed (Claude Code path OR dev path).
if [ ! -f "$HOME/.claude/skills/auto-loop/SKILL.md" ] && [ ! -f "$HOME/skills/skills/auto-loop/SKILL.md" ]; then
  echo "delegate-to-auto-loop.sh: vd:auto-loop not installed. Run '/plugin install vd@vd-skills' (marketplace) or 'vd install claude auto-loop' (dev)." >&2
  exit 3
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYBIN="${HOME}/.claude/skills/.venv/bin/python3"; [ -x "$PYBIN" ] || PYBIN="$(command -v python3)"

# Build the compound verifier script.
VERIFY_SH="$(bash "${SCRIPT_DIR}/build-compound-verifier.sh" --goal-dir "$GOAL_DIR" --action "$ACTION" --iter "$ITER")"; rc=$?
if [ "$rc" -ne 0 ]; then
  echo "delegate-to-auto-loop.sh: cannot delegate — no per-action verifier bound to '$ACTION'" >&2
  exit 5
fi

# Read budget caps from goal.yaml → translate to auto-loop --max-* flags.
read_budgets() {
  GOAL_DIR="$GOAL_DIR" "$PYBIN" - <<'PY'
import os, yaml, shlex
g = yaml.safe_load(open(os.path.join(os.environ["GOAL_DIR"], "goal.yaml")))
b = g.get("budgets") or {}
slug = g.get("slug", "goal")
def q(v): return shlex.quote(str(v) if v is not None else "")
print(f"GOAL_SLUG={q(slug)}")
print(f"MAX_ITER={q(b.get('max_iterations', 30))}")
# token_pct_cap is a percentage; estimate absolute via 2M ceiling
tok_pct = int(b.get("token_pct_cap", 80) or 80)
print(f"MAX_TOKENS={q(int(tok_pct * 20000))}")   # 80% of ~2M ≈ 1.6M
print(f"MAX_WALLCLOCK={q('4h')}")                 # auto-loop's floor; keep as default
PY
}
eval "$(read_budgets)"

# Write the marker file so resume can detect mid-delegation.
MARKER_DIR="${GOAL_DIR}/.pursue"
mkdir -p "$MARKER_DIR"
MARKER="${MARKER_DIR}/delegated-to-auto-loop.json"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
"$PYBIN" - "$MARKER" "$ACTION" "$VERIFY_SH" "$NOW" <<'PY'
import sys, json
out = {"action": sys.argv[2], "verify_script": sys.argv[3], "delegated_at": sys.argv[4]}
json.dump(out, open(sys.argv[1], "w"), indent=2)
PY

# Detect runtime — Codex needs `--codex` flag appended so auto-loop delegates
# to native /goal instead of running its Stop-hook in-house loop.
PURSUE_RUNTIME_DETECTED="$(bash "${SCRIPT_DIR}/detect-runtime.sh" 2>/dev/null || echo unknown)"
CODEX_FLAG=""
if [ "$PURSUE_RUNTIME_DETECTED" = "codex" ]; then
  CODEX_FLAG="--codex"
fi

# Emit the invocation hint as JSON. SKILL.md interprets and calls the Skill tool.
ACTION="$ACTION" GOAL_SLUG="$GOAL_SLUG" VERIFY_SH="$VERIFY_SH" \
  MAX_ITER="$MAX_ITER" MAX_TOKENS="$MAX_TOKENS" MAX_WALLCLOCK="$MAX_WALLCLOCK" \
  MARKER="$MARKER" CODEX_FLAG="$CODEX_FLAG" \
  "$PYBIN" - <<'PY'
import os, json, shlex
goal = f"pursue:{os.environ['ACTION']} for {os.environ['GOAL_SLUG']} until verifier passes"
codex_flag = (" " + os.environ["CODEX_FLAG"]) if os.environ.get("CODEX_FLAG") else ""
args = (
    f'{shlex.quote(goal)} '
    f'--verify {shlex.quote(os.environ["VERIFY_SH"])} '
    f'--max-iterations {os.environ["MAX_ITER"]} '
    f'--max-tokens {os.environ["MAX_TOKENS"]} '
    f'--max-wallclock {os.environ["MAX_WALLCLOCK"]}'
    f'{codex_flag}'
)
print(json.dumps({
    "dispatch_kind": "skill",
    "skill": "vd:auto-loop",
    "args": args,
    "marker": os.environ["MARKER"],
    "verify_script": os.environ["VERIFY_SH"],
}))
PY
