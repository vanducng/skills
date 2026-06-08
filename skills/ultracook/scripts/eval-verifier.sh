#!/usr/bin/env bash
# eval-verifier.sh — evaluate one verifier; return JSON outcome on stdout.
#
# Usage variants (one per type):
#   --type ci_green --pr-number N [--repo X]
#   --type pod_image_matches --deployment D --namespace NS --expected-image IMG [--kube-context K]
#   --type http_status --url U [--expected-code 200] [--header "Key: Val"...]
#   --type cmd_exits_zero --cmd "..." [--cwd .]
#   --type test_suite_passes --target "..."
#   --type manual_confirm --prompt "..."   (returns needs_user_input sentinel)
#   --type manual_confirm --resolve <yes|no> --prompt "..."  (records the answer)
#   --type shell --cmd "..." [--expected-exit 0] [--expected-output-contains "..."]
#
# Stdout: JSON {"pass": bool|null, "evidence": str, "latency_ms": int, [needs_user_input: bool, prompt: str]}
# Exit: 0 on normal evaluation (pass=false is data, not error); 2 on verifier crash.

set -uo pipefail   # NOT errexit — we WANT to capture non-zero exits

TYPE=""
declare -A ARGS=()
HEADERS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --type)                       TYPE="${2:?}"; shift 2 ;;
    --pr-number|--repo|--deployment|--namespace|--expected-image|--kube-context|--url|--expected-code|--cmd|--cwd|--target|--prompt|--resolve|--expected-exit|--expected-output-contains)
      key="${1#--}"
      ARGS["$key"]="${2:-}"; shift 2 ;;
    --header)                     HEADERS+=("${2:?}"); shift 2 ;;
    --help|-h)                    echo "see header docstring"; exit 0 ;;
    *) echo "eval-verifier.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done

[ -z "$TYPE" ] && { echo "eval-verifier.sh: --type required" >&2; exit 2; }

START_MS=$(($(date +%s%N) / 1000000))

# ── JSON output helper ────────────────────────────────────────────────────────
# emit <pass-token> <evidence> [<extras-json>]
#   pass-token: literal "true" | "false" | "null"
#   evidence:   free-form string
#   extras:     optional JSON object (defaults to {})
emit() {
  local pass="$1" evidence="$2" extras="${3:-{\}}"
  local end_ms=$(($(date +%s%N) / 1000000))
  local lat=$((end_ms - START_MS))
  PYBIN="${HOME}/.claude/skills/.venv/bin/python3"
  [ -x "$PYBIN" ] || PYBIN="$(command -v python3)"
  PASS="$pass" EVIDENCE="$evidence" EXTRAS="$extras" LAT="$lat" "$PYBIN" - <<'PY'
import json, os
pass_map = {"true": True, "false": False, "null": None}
out = {"pass": pass_map.get(os.environ["PASS"], None),
       "evidence": os.environ["EVIDENCE"],
       "latency_ms": int(os.environ["LAT"])}
extras = json.loads(os.environ["EXTRAS"])
if isinstance(extras, dict):
    out.update(extras)
print(json.dumps(out))
PY
}

case "$TYPE" in

  ci_green)
    pr="${ARGS[pr-number]:-}"; repo="${ARGS[repo]:-}"
    [ -z "$pr" ] && { emit null "ci_green missing pr-number" '{"error": "missing_arg"}'; exit 0; }
    repo_arg=""; [ -n "$repo" ] && repo_arg="--repo $repo"
    json="$(gh pr checks "$pr" $repo_arg --json name,bucket,conclusion 2>&1)" || true
    if ! echo "$json" | head -1 | grep -q '^\['; then
      emit false "ci_green: gh failed: $(printf '%.200s' "$json")" "{}"
      exit 0
    fi
    # all bucket != "pending" AND all conclusion == "success"
    PYBIN="${HOME}/.claude/skills/.venv/bin/python3"; [ -x "$PYBIN" ] || PYBIN="$(command -v python3)"
    all_done="$(printf '%s' "$json" | "$PYBIN" -c 'import json,sys; d=json.load(sys.stdin); print("yes" if d and all(c.get("bucket")!="pending" for c in d) else "no")')"
    all_ok="$(printf '%s' "$json" | "$PYBIN" -c 'import json,sys; d=json.load(sys.stdin); print("yes" if d and all(c.get("conclusion")=="success" for c in d) else "no")')"
    counts="$(printf '%s' "$json" | "$PYBIN" -c 'import json,sys; d=json.load(sys.stdin); print(", ".join(f"{c[\"name\"]}: {c.get(\"conclusion\") or c[\"bucket\"]}" for c in d))')"
    if [ "$all_done" = "yes" ] && [ "$all_ok" = "yes" ]; then
      emit true "ci_green: all checks pass ($counts)" "{}"
    else
      emit false "ci_green: not all green ($counts)" "{}"
    fi
    ;;

  pod_image_matches)
    dep="${ARGS[deployment]:-}"; ns="${ARGS[namespace]:-}"; expected="${ARGS[expected-image]:-}"; ctx="${ARGS[kube-context]:-}"
    if [ -z "$dep" ] || [ -z "$ns" ] || [ -z "$expected" ]; then
      emit null "pod_image_matches missing args" '{"error":"missing_arg"}'; exit 0
    fi
    ctx_arg=""; [ -n "$ctx" ] && ctx_arg="--context $ctx"
    actual="$(kubectl $ctx_arg get deployment "$dep" -n "$ns" -o jsonpath='{.spec.template.spec.containers[0].image}' 2>&1)" || true
    if [ "$actual" = "$expected" ]; then
      emit true "pod_image_matches: $actual" "{}"
    else
      emit false "pod_image_matches: expected $expected, got $actual" "{}"
    fi
    ;;

  http_status)
    url="${ARGS[url]:-}"; code="${ARGS[expected-code]:-200}"
    [ -z "$url" ] && { emit null "http_status missing url" '{"error":"missing_arg"}'; exit 0; }
    hdr_args=()
    for h in "${HEADERS[@]}"; do hdr_args+=(-H "$h"); done
    actual="$(curl -s -o /dev/null -w '%{http_code}' "${hdr_args[@]}" "$url" 2>&1 || echo "000")"
    if [ "$actual" = "$code" ]; then
      emit true "http_status $url → $actual" "{}"
    else
      emit false "http_status $url → $actual (expected $code)" "{}"
    fi
    ;;

  cmd_exits_zero|test_suite_passes)
    cmd="${ARGS[cmd]:-${ARGS[target]:-}}"
    cwd="${ARGS[cwd]:-.}"
    [ -z "$cmd" ] && { emit null "$TYPE missing cmd/target" '{"error":"missing_arg"}'; exit 0; }
    out="$(cd "$cwd" && eval "$cmd" 2>&1)"; rc=$?
    if [ "$rc" -eq 0 ]; then
      emit true "$TYPE: $cmd → exit 0" "{}"
    else
      tail_out="$(printf '%s' "$out" | tail -c 300)"
      emit false "$TYPE: $cmd → exit $rc | tail: $tail_out" "{}"
    fi
    ;;

  manual_confirm)
    prompt="${ARGS[prompt]:-confirm?}"
    resolve="${ARGS[resolve]:-}"
    if [ -z "$resolve" ]; then
      # First call: emit sentinel; SKILL.md handles AskUserQuestion.
      PYBIN="${HOME}/.claude/skills/.venv/bin/python3"; [ -x "$PYBIN" ] || PYBIN="$(command -v python3)"
      PROMPT="$prompt" "$PYBIN" - <<'PY'
import json, os
print(json.dumps({"pass": None,
                  "evidence": "manual_confirm: awaiting user",
                  "latency_ms": 0,
                  "needs_user_input": True,
                  "prompt": os.environ["PROMPT"]}))
PY
    else
      case "$resolve" in
        yes|y|Yes|YES) emit true  "manual_confirm: user said yes ($prompt)" ;;
        *)             emit false "manual_confirm: user said no ($prompt)"  ;;
      esac
    fi
    ;;

  shell)
    cmd="${ARGS[cmd]:-}"; expected_exit="${ARGS[expected-exit]:-0}"; expected_contains="${ARGS[expected-output-contains]:-}"
    [ -z "$cmd" ] && { emit null "shell missing cmd" '{"error":"missing_arg"}'; exit 0; }
    out="$(eval "$cmd" 2>&1)"; rc=$?
    pass="true"
    why=""
    if [ "$rc" -ne "$expected_exit" ]; then pass="false"; why="exit $rc (expected $expected_exit)"; fi
    if [ "$pass" = "true" ] && [ -n "$expected_contains" ]; then
      if ! printf '%s' "$out" | grep -qF -- "$expected_contains"; then
        pass="false"; why="output missing '$expected_contains'"
      fi
    fi
    tail_out="$(printf '%s' "$out" | tail -c 300)"
    if [ "$pass" = "true" ]; then
      emit true "shell: $cmd → exit $rc" "{}"
    else
      emit false "shell: $cmd → $why | tail: $tail_out" "{}"
    fi
    ;;

  *)
    emit null "unknown verifier type: $TYPE" "{\"error\":\"unknown_type\"}"
    exit 2
    ;;
esac
