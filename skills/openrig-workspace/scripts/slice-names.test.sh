#!/usr/bin/env bash
# Tests for slice-names.cjs. Run: bash skills/openrig-workspace/scripts/slice-names.test.sh
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$DIR/slice-names.cjs"
pass=0
fail=0
ok()  { pass=$((pass+1)); echo "  ✓ $1"; }
bad() { fail=$((fail+1)); echo "  ✗ $1"; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
touch "$TMP/workspace.yaml"
MISSIONS="$TMP/orgs/acme/shop/missions"

slice() { mkdir -p "$MISSIONS/$1/slices/$2"; echo "$MISSIONS/$1/slices/$2"; }
spec() { printf '%b' "$2" > "$MISSIONS/$1/SPEC.md"; }

assert_field() {
  local desc="$1" field="$2" want="$3"
  shift 3
  local got
  got="$(node "$RUNNER" "$@" --json | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const v=JSON.parse(s)[process.argv[1]];console.log(typeof v==="object"?JSON.stringify(v):String(v))})' "$field")"
  if [[ "$got" == "$want" ]]; then ok "$desc"; else bad "$desc (got $got, want $want)"; fi
}

assert_fails() {
  local desc="$1" pattern="$2"
  shift 2
  local out
  if out="$(node "$RUNNER" "$@" 2>&1)"; then
    bad "$desc (exit 0)"
  elif [[ "$out" == *"$pattern"* ]]; then
    ok "$desc"
  else
    bad "$desc (message: $out)"
  fi
}

echo "folder fallback"
S="$(slice m2-checkout 04-login-fix)"
assert_field "slice id from the m<n>- prefix" sliceId "m2-s04" "$S"
assert_field "no ticket leaves it out of the branch" branch "feat/m2-s04-login-fix" "$S"
assert_field "no ticket means no PR tag" prTag "null" "$S"
assert_field "worktree under the workspace root" worktrees "[{\"repo\":\"api\",\"name\":\"api-m2-s04\",\"path\":\"$TMP/.worktrees/api-m2-s04\"}]" "$S" --repo api

echo "frontmatter"
S="$(slice q3-billing 07-refunds)"
spec q3-billing '---\r\nid: X\r\ncode: m7\r\nticket: ABC-123  # main ticket\r\nmilestone: "07"\r\n---\r\n# Mission\r\n'
assert_field "CRLF frontmatter and a trailing comment parse" prTag "[ABC-123|M7|S7]" "$S"
assert_field "branch carries type, ticket, slice id and slug" branch "fix/ABC-123-m7-s07-refunds" "$S" --type fix
assert_field "follow-up branch adds -2" followUpBranch "feat/ABC-123-m7-s07-refunds-2" "$S"

echo "rejections"
assert_fails "mission without prefix or code" "Set code:" "$(slice billing 01-x)"
spec q3-billing '---\ncode: m7-billing\n---\n'
assert_fails "invalid code is named as invalid" "must match" "$S"
spec q3-billing '---\ncode: m7\nticket: abc 123\n---\n'
assert_fails "invalid ticket" "must look like ABC-123" "$S"
spec q3-billing '---\ncode: m7\n---\n'
assert_fails "repo name with a dot" "lowercase letters, digits or '-'" "$S" --repo api.v2
assert_fails "worktree name past 63 characters" "63-character" "$S" --repo "$(printf 'r%.0s' {1..60})"
assert_fails "folder that is not <nn>-<slug>" "not a slice folder" "$(slice m2-checkout login)"
assert_fails "--type given twice" "Pass --type once" "$S" --type fix --type feat
spec q3-billing '---\ncode: m7\nticket: "ABC-9" # main\nmilestone: 7 # q3\n---\n'
assert_field "trailing comment dropped from quoted and unquoted values" prTag "[ABC-9|M7|S7]" "$S"

echo
echo "$pass passed, $fail failed"
[[ "$fail" == 0 ]]
