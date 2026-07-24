#!/usr/bin/env bash
# eval-dod.sh - evaluate a plan's "## Definition of Done" verifiers.
# The mechanical form of vd:cook's final goal gate; vd:plan uses --lint to validate
# the block it writes. Vocab mirrors vd:ultracook's verifier-vocab (local subset).
# Plain shell only → runs identically under Claude Code and Codex.
#
# Usage:
#   eval-dod.sh <plan.md>            run every DoD verifier; exit 0 iff all pass
#   eval-dod.sh --lint <plan.md>     validate the block only (known types, non-empty args); no execution
#   eval-dod.sh --type <t> --arg <a> evaluate a single verifier
#
# DoD line format (one per line under "## Definition of Done"): - <type>: <arg>
#   test_suite_passes: <test cmd>     pass = exit 0
#   cmd_exits_zero: <cmd>             pass = exit 0
#   shell: <cmd>                      pass = exit 0
#   http_status: <url> [code]         pass = HTTP status == code (default 200)
#   manual_confirm: <prompt>          needs user - never auto-passes (gate reports it)
#   ci_green / pod_image_matches      workflow-level - belong to vd:ultracook, not this gate
#
# Exit: 0 all pass · 1 one-or-more unmet/needs-user · 2 usage/parse error.
set -uo pipefail

KNOWN_TYPES="test_suite_passes cmd_exits_zero shell http_status manual_confirm ci_green pod_image_matches"
LOCAL_TYPES="test_suite_passes cmd_exits_zero shell http_status"

die() { echo "eval-dod: $*" >&2; exit 2; }

# Resolve a plan path; a relative .workbench/ path from a linked worktree belongs to the main checkout.
resolve_plan() {
  local plan="$1" main
  if [ ! -f "$plan" ] && [ "${plan#/}" = "$plan" ]; then
    main=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || main=""
    main="${main%/.git}"
    [ -n "$main" ] && [ -f "$main/$plan" ] && plan="$main/$plan"
  fi
  [ -f "$plan" ] || die "plan file not found: $plan"
  printf '%s' "$plan"
}

# Print the verifier lines ("<type>\t<arg>") from a plan.md's DoD section.
parse_dod() {
  local plan="$1"
  awk '
    /^##[[:space:]]+Definition of Done/ { inblk=1; next }
    inblk && /^##[[:space:]]/           { inblk=0 }
    inblk {
      line=$0
      sub(/^[[:space:]]*/, "", line)
      if (line ~ /^<!--/ || line ~ /^#/ || line == "") next   # comments / blank
      if (line ~ /^-[[:space:]]+/) {
        sub(/^-[[:space:]]+/, "", line)
        i = index(line, ":")
        if (i == 0) next
        type = substr(line, 1, i-1)
        arg  = substr(line, i+1)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", type)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", arg)
        if (type != "") printf "%s\t%s\n", type, arg
      }
    }
  ' "$plan"
}

# eval_one <type> <arg> → echoes "PASS|FAIL|NEEDS_USER <evidence>"; never exits.
eval_one() {
  local type="$1" arg="$2" out code
  case "$type" in
    test_suite_passes|cmd_exits_zero|shell)
      [ -n "$arg" ] || { echo "FAIL (empty command)"; return; }
      out=$(bash -c "$arg" 2>&1); code=$?
      if [ $code -eq 0 ]; then echo "PASS (exit 0)"
      else echo "FAIL (exit $code: $(printf '%s' "$out" | tail -1))"; fi
      ;;
    http_status)
      local url want got
      url=$(printf '%s' "$arg" | awk '{print $1}')
      want=$(printf '%s' "$arg" | awk '{print ($2==""?200:$2)}')
      [ -n "$url" ] || { echo "FAIL (no url)"; return; }
      got=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$url" 2>/dev/null || echo 000)
      if [ "$got" = "$want" ]; then echo "PASS ($got)"
      else echo "FAIL (got $got, want $want)"; fi
      ;;
    manual_confirm)
      echo "NEEDS_USER ($arg)"
      ;;
    ci_green|pod_image_matches)
      echo "FAIL (workflow-level verifier - run via vd:ultracook, not the cook gate)"
      ;;
    *)
      echo "FAIL (unknown verifier type: $type)"
      ;;
  esac
}

cmd_lint() {
  local plan
  plan=$(resolve_plan "$1") || exit $?
  local n=0 bad=0
  while IFS=$'\t' read -r type arg; do
    [ -z "$type" ] && continue
    n=$((n+1))
    if ! printf '%s ' $KNOWN_TYPES | grep -qw "$type"; then
      echo "  ✗ unknown type: $type"; bad=$((bad+1))
    elif [ -z "$arg" ]; then
      echo "  ✗ $type: missing arg"; bad=$((bad+1))
    else
      echo "  ✓ $type"
    fi
  done < <(parse_dod "$plan")
  if [ "$n" -eq 0 ]; then echo "  (no ## Definition of Done verifiers found)"; return 1; fi
  [ "$bad" -eq 0 ] || { echo "lint: $bad invalid verifier(s)"; return 1; }
  echo "lint: $n verifier(s) OK"; return 0
}

cmd_run() {
  local plan
  plan=$(resolve_plan "$1") || exit $?
  local n=0 fail=0 result evidence
  echo "🔒 Goal gate - ## Definition of Done ($plan)"
  while IFS=$'\t' read -r type arg; do
    [ -z "$type" ] && continue
    n=$((n+1))
    out=$(eval_one "$type" "$arg")
    result=${out%% *}; evidence=${out#* }
    case "$result" in
      PASS)        echo "  ✅ $type: $arg  $evidence" ;;
      NEEDS_USER)  echo "  ⏸  $type: $evidence (needs user confirmation)"; fail=$((fail+1)) ;;
      *)           echo "  ⛔ $type: $arg  $evidence"; fail=$((fail+1)) ;;
    esac
  done < <(parse_dod "$plan")
  if [ "$n" -eq 0 ]; then echo "  (no Definition of Done block - fall back to plan-level Success Criteria)"; return 1; fi
  echo "---"
  if [ "$fail" -eq 0 ]; then echo "✅ goal ACHIEVED - $n/$n verifiers pass"; return 0
  else echo "⛔ goal UNMET - $fail/$n unmet; do not claim done, kick back to the relevant phase"; return 1; fi
}

# ── arg dispatch ──────────────────────────────────────────────────────────────
[ $# -ge 1 ] || die "usage: eval-dod.sh <plan.md> | --lint <plan.md> | --type <t> --arg <a>"

case "$1" in
  --lint)  [ $# -ge 2 ] || die "--lint needs <plan.md>"; cmd_lint "$2" ;;
  --type)
    type=""; arg=""
    while [ $# -gt 0 ]; do
      case "$1" in
        --type) type="${2:-}"; shift 2 ;;
        --arg)  arg="${2:-}"; shift 2 ;;
        *) die "unknown arg: $1" ;;
      esac
    done
    [ -n "$type" ] || die "--type required"
    out=$(eval_one "$type" "$arg"); echo "$out"
    [ "${out%% *}" = "PASS" ]
    ;;
  -h|--help) sed -n '2,20p' "$0" ;;
  *) cmd_run "$1" ;;
esac
