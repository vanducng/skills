#!/usr/bin/env bash
# Tests for the watch_access read-only guard in check-resources.sh. Run: bash skills/openrig-workspace/scripts/check-resources.test.sh
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK="$DIR/check-resources.sh"
pass=0
fail=0
ok()  { pass=$((pass+1)); echo "  ✓ $1"; }
bad() { fail=$((fail+1)); echo "  ✗ $1"; }
command -v yq >/dev/null || { echo "yq (mikefarah v4) is required"; exit 2; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
P="$TMP/orgs/acme/projects/shop"
mkdir -p "$P"
printf 'schema: projects.contacts/v1\norg: acme\ncontacts: {}\n' > "$TMP/orgs/acme/contacts.yaml"
printf 'schema: projects.resources/v2\n' > "$P/resources.yaml"

org() { printf 'schema: projects.resources/v2\norg: acme\n%s\n' "$1" > "$TMP/orgs/acme/resources.yaml"; }
# expect <description> <exit code> <output fragment or ""> ; the org file is already written
expect() {
  local desc="$1" want="$2" frag="$3" out code
  out="$(bash "$CHECK" "$P" 2>&1)"; code=$?
  if [[ $code == "$want" && ( -z "$frag" || "$out" == *"$frag"* ) ]]; then ok "$desc"; else bad "$desc (exit $code: $out)"; fi
}

echo "org watch_access"
org 'watch_access:
  order: [history, aside]
  aside: {account: u1, guide_first: true, open_conversation: read_only, post: never}'
expect "post: never passes" 0 "ok:"
org 'watch_access:
  aside: {account: u1, post: allowed}'
expect "post: allowed fails and names the entry" 1 "FAIL: watch_access.aside (account u1) in $TMP/orgs/acme/resources.yaml must have post: never, has 'allowed'"
org 'watch_access:
  aside: {account: u1, guide_first: true}'
expect "a missing post fails" 1 "has 'unset'"
org 'watch_access:
  aside: {account: u1, post: false}'
expect "post: false is not never" 1 "has 'false'"
org 'watch_access:
  aside:
    - {account: u1, post: never}
    - {account: u2, post: owner-only}'
expect "a list of aside entries: the bad one is named" 1 "account u2"
org 'watch_access:
  aside:
    - {account: u1, post: never}
    - {account: u2, post: never}'
expect "a list where every entry is never passes" 0 "ok:"
org 'watch_access:
  gog: {account: a, readonly: true}'
expect "no aside entry passes" 0 "ok:"
org 'conversations: []'
expect "no watch_access passes" 0 "ok:"
rm "$TMP/orgs/acme/resources.yaml"
expect "no org file passes" 0 "ok:"

echo "project watch_access"
org 'watch_access:
  aside: {account: u1, post: never}'
printf 'schema: projects.resources/v2\nwatch_access:\n  aside: {account: u9, post: allowed}\n' > "$P/resources.yaml"
expect "the project file is checked too" 1 "account u9"
printf 'schema: projects.resources/v2\n' > "$P/resources.yaml"

echo "the other checks still run"
org 'watch_access:
  aside: {account: u1, post: allowed}'
printf 'schema: projects.resources/v2\ncontacts:\n  - {ref: nobody, role: x}\n' > "$P/resources.yaml"
out="$(bash "$CHECK" "$P" 2>&1)"
[[ "$out" == *"contact 'nobody'"* && "$out" == *"must have post: never"* ]] && ok "both findings are reported in one run" || bad "findings: $out"

echo
echo "$pass passed, $fail failed"
[[ "$fail" == 0 ]]
