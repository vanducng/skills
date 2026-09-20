#!/usr/bin/env bash
# check-jev-gates.sh - calibration eval for the jev gates encoded in
# cook, code-review, and guide, plus the shared browser success-check pattern
# that browser-skill encodes (that skill lands via its own PR). Replays fixture
# states against the live TypeSafe API and asserts each gate routes as its
# skill table says.
#
# Usage:
#   bash scripts/check-jev-gates.sh [--cases <file>]
#
# Requires jq + curl and TYPESAFE_API_KEY in the environment. No key ->
# SKIP (exit 0): jev gates never block, CI without secrets stays green.
#
# Fixture format: one JSON object per line:
#   {"id":"...","skill":"...","gate":"...","state":"...",
#    "question":{"type":"noul","instructions":"...","criteria":{"true":"...","false":"..."}},
#    "expect":{"noul":[min,max]}}
# Choice cases use "criteria":{"<option>":"<rubric>",...} and "expect":{"choice":"<option>","pmin":0.6}
# (pmin optional: minimum winning probability, e.g. guide's 0.6 route).
# Exit: 0 all pass (or skip) - 1 calibration or API failure - 2 usage error.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CASES="${REPO}/scripts/jev-gates-cases.jsonl"
API="https://api.typesafe.ai/v1/systemone"

while [ $# -gt 0 ]; do
  case "$1" in
    --cases)
      [ $# -ge 2 ] || { echo "usage: $0 [--cases <file>]" >&2; exit 2; }
      CASES="$2"; shift 2 ;;
    *) echo "usage: $0 [--cases <file>]" >&2; exit 2 ;;
  esac
done

command -v jq >/dev/null 2>&1 || { echo "FAIL: jq required" >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "FAIL: curl required" >&2; exit 1; }
[ -f "$CASES" ] || { echo "FAIL: cases file not found: $CASES" >&2; exit 2; }
if [ -z "${TYPESAFE_API_KEY:-}" ]; then
  echo "SKIP: TYPESAFE_API_KEY not set"
  exit 0
fi

while IFS= read -r line; do
  [ -n "$line" ] || continue
  jq -e 'has("id") and has("skill") and has("gate") and has("state") and has("question") and ((.expect.noul? | type == "array" and length == 2) or (.expect.choice? | type == "string"))' \
    <<<"$line" >/dev/null 2>&1 || { echo "FAIL: malformed case line: ${line:0:60}" >&2; exit 2; }
done < "$CASES"

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

pass=0
fail=0
while IFS= read -r line; do
  [ -n "$line" ] || continue
  label="$(jq -r '"\(.skill)/\(.gate)"' <<<"$line")"
  payload="$(jq -n \
    --arg state "$(jq -r '.state' <<<"$line")" \
    --argjson q "$(jq -c '.question' <<<"$line")" \
    '{state: $state, model: "jev-latest", questions: {gate: $q}}')"

  code=""
  for _ in 1 2; do
    code="$(curl -sS -m 30 -o "$TMP" -w '%{http_code}' \
      -H "Authorization: Bearer ${TYPESAFE_API_KEY}" \
      -H 'Content-Type: application/json' \
      -d "$payload" "$API" 2>/dev/null || echo 000)"
    [ "$code" = "200" ] && break
    sleep 2
  done
  if [ "$code" != "200" ]; then
    echo "FAIL  $label  api http=$code"
    fail=$((fail + 1))
    continue
  fi

  if jq -e 'has("noul")' <<<"$(jq -c '.expect // {}' <<<"$line")" >/dev/null 2>&1; then
    p="$(jq -r '.answers.gate.noul // empty' "$TMP")"
    lo="$(jq -r '.expect.noul[0]' <<<"$line")"
    hi="$(jq -r '.expect.noul[1]' <<<"$line")"
    if [ -n "$p" ] && awk -v p="$p" -v lo="$lo" -v hi="$hi" 'BEGIN{exit !(p>=lo && p<=hi)}'; then
      echo "PASS  $label  noul=$p in [$lo,$hi]"
      pass=$((pass + 1))
    else
      echo "FAIL  $label  noul=${p:-none} expected in [$lo,$hi]"
      fail=$((fail + 1))
    fi
  else
    want="$(jq -r '.expect.choice' <<<"$line")"
    got="$(jq -r '.answers.gate.choice // empty' "$TMP")"
    prob="$(jq -r --arg w "$want" '.answers.gate.probabilities[$w] // 0' "$TMP")"
    pmin="$(jq -r '.expect.pmin // 0' <<<"$line")"
    if [ -n "$got" ] && [ "$got" = "$want" ] && awk -v p="$prob" -v m="$pmin" 'BEGIN{exit !(p>=m)}'; then
      echo "PASS  $label  choice=$got p=$prob"
      pass=$((pass + 1))
    else
      echo "FAIL  $label  choice=${got:-none} expected $want"
      fail=$((fail + 1))
    fi
  fi
done < "$CASES"

echo "---"
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
