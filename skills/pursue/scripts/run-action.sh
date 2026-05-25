#!/usr/bin/env bash
# run-action.sh — resolve the dispatch for ONE action; either:
#   - execute it (shell type), capturing output to iterations/NNN-{action}.log
#   - OR emit a JSON "invocation hint" for SKILL.md to dispatch via Skill /
#     Agent / Monitor tools.
#
# The two-layer pattern (see references/architecture.md): bash can't call
# Skill/Agent/Monitor directly. So this script returns the next-tool-call
# spec on stdout and SKILL.md interprets it.
#
# Usage: run-action.sh --goal-dir <dir> --action <name>
#
# Stdout JSON shape:
#   { "dispatch_kind": "skill" | "agent" | "monitor" | "shell" | "terminal",
#     "skill": "<vd:...>"           # when kind=skill
#     "subagent_type": "<...>"       # when kind=agent
#     "args": "<arg string>",
#     "shell_cmd": "<cmd>"           # when kind=shell or monitor
#     "log_path": "<path>",
#     "verifier": {<spec or null>}
#   }
#
# Side effects: for kind=shell, runs the command and writes the log file.
# For other kinds, no side effects — SKILL.md does the actual call.

set -uo pipefail

GOAL_DIR=""; ACTION=""
while [ $# -gt 0 ]; do
  case "$1" in
    --goal-dir) GOAL_DIR="${2:?}"; shift 2 ;;
    --action)   ACTION="${2:?}"; shift 2 ;;
    *) echo "run-action.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done

[ -z "$GOAL_DIR" ] && { echo "--goal-dir required" >&2; exit 2; }
[ -z "$ACTION" ]   && { echo "--action required" >&2; exit 2; }
[ -f "${GOAL_DIR}/state.json" ] || { echo "state.json missing in $GOAL_DIR" >&2; exit 2; }
[ -f "${GOAL_DIR}/goal.yaml" ]   || { echo "goal.yaml missing in $GOAL_DIR" >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VOCAB="$(dirname "$SCRIPT_DIR")/references/action-vocab.yaml"

PYBIN="${HOME}/.claude/skills/.venv/bin/python3"; [ -x "$PYBIN" ] || PYBIN="$(command -v python3)"

# Determine next iteration number for log naming (same algorithm as append-journal.sh).
ITER_DIR="${GOAL_DIR}/iterations"
mkdir -p "$ITER_DIR"
N=$(( $(find "$ITER_DIR" -maxdepth 1 -name '[0-9][0-9][0-9]-*.md' -type f 2>/dev/null | wc -l | tr -d ' ') + 1 ))
NNN="$(printf '%03d' "$N")"
LOG_PATH="${ITER_DIR}/${NNN}-${ACTION}.log"

# Look up the action vocab entry + interpolate placeholders from goal.yaml + state.json + profile.
"$PYBIN" - "$VOCAB" "$ACTION" "$GOAL_DIR" "$LOG_PATH" "$SCRIPT_DIR" <<'PY'
import sys, os, json, yaml, tomllib, subprocess, shlex, re, time

vocab_path, action, goal_dir, log_path, script_dir = sys.argv[1:6]

vocab = yaml.safe_load(open(vocab_path))
entry = vocab.get('actions', {}).get(action)
if not entry:
    print(json.dumps({"error": f"unknown action: {action}"}))
    sys.exit(3)

goal  = yaml.safe_load(open(os.path.join(goal_dir, 'goal.yaml')))
state = json.load(open(os.path.join(goal_dir, 'state.json')))

# Resolve profile path via lookup-profile.sh.
remote_url = (goal.get('project') or {}).get('remote_url', '')
look = subprocess.run([os.path.join(script_dir, 'lookup-profile.sh'), '--remote-url', remote_url],
                     capture_output=True, text=True)
profile_path = look.stdout.strip() if look.returncode == 0 else os.path.join(os.path.dirname(script_dir), 'projects', '_default.toml')
profile = tomllib.load(open(profile_path, 'rb'))

# Build placeholder map.
placeholders = {
    "plan_dir": goal.get('plan_dir', ''),            # set after `plan` action completes
    "pr_number": state.get('pr_number', ''),
    "run_id": state.get('image_build_run_id', ''),
    "ship_mode": (profile.get('project') or {}).get('ship_mode', 'official'),
    "repo": (goal.get('project') or {}).get('remote_url', ''),
    "profile.test_cmd": (profile.get('verify') or {}).get('test_cmd', ''),
    "profile.deploy.reconcile_cmd": (profile.get('deploy') or {}).get('reconcile_cmd', ''),
    "profile.deploy.rollout_cmd":   (profile.get('deploy') or {}).get('rollout_cmd', ''),
    "profile.verify.deployment":    (profile.get('verify') or {}).get('deployment', ''),
    "profile.verify.namespace":     (profile.get('verify') or {}).get('namespace', ''),
    "profile.verify.smoke_cmd":     (profile.get('verify') or {}).get('smoke_cmd', ''),
    "profile.kube_context":         (profile.get('verify') or {}).get('kube_context', ''),
}

def interp(s):
    if not s: return s
    for k, v in placeholders.items():
        s = s.replace('{' + k + '}', str(v))
    return s

dispatch = entry.get('dispatch', '')
args = interp(entry.get('args', '') or '')

# Parse dispatch type prefix.
if dispatch == 'terminal':
    out = {"dispatch_kind": "terminal", "action": action, "log_path": log_path, "verifier": None}
elif dispatch.startswith('skill:'):
    out = {"dispatch_kind": "skill", "skill": dispatch[len('skill:'):], "args": args, "log_path": log_path,
           "verifier": entry.get('verifier')}
elif dispatch.startswith('agent:'):
    out = {"dispatch_kind": "agent", "subagent_type": dispatch[len('agent:'):], "args": args, "log_path": log_path,
           "verifier": entry.get('verifier')}
elif dispatch.startswith('monitor:'):
    cmd = interp(dispatch[len('monitor:'):])
    out = {"dispatch_kind": "monitor", "shell_cmd": cmd, "log_path": log_path, "verifier": entry.get('verifier')}
elif dispatch.startswith('shell:'):
    cmd = interp(dispatch[len('shell:'):])
    # Execute the shell command, capturing output.
    t0 = time.time()
    with open(log_path, 'w') as logf:
        proc = subprocess.run(cmd, shell=True, stdout=logf, stderr=subprocess.STDOUT)
    out = {"dispatch_kind": "shell", "shell_cmd": cmd, "exit_code": proc.returncode,
           "duration_ms": int((time.time() - t0) * 1000), "log_path": log_path,
           "verifier": entry.get('verifier')}
else:
    out = {"dispatch_kind": "unknown", "dispatch": dispatch, "error": "unrecognized dispatch prefix"}

print(json.dumps(out, indent=2))
PY
