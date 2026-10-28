#!/usr/bin/env bash
# Validate a project's resources.yaml against its org contacts.yaml and scan both for private data.
# Usage: check-resources.sh <project dir>   (orgs/<org>/projects/<project>)
set -euo pipefail

proj="${1:?usage: check-resources.sh <project dir>}"
res="$proj/resources.yaml"
org="$(cd "$proj/../.." && pwd)"
contacts="$org/contacts.yaml"
command -v yq >/dev/null || { echo "yq (mikefarah v4) is required" >&2; exit 2; }
[[ -f "$res" ]] || { echo "missing $res" >&2; exit 1; }

fail=0
report() { echo "FAIL: $*"; fail=1; }

yq '.' "$res" >/dev/null || report "$res does not parse"
if [[ -f "$contacts" ]]; then
  yq '.' "$contacts" >/dev/null || report "$contacts does not parse"
  keys="$(yq '.contacts | keys | .[]' "$contacts")"
else
  keys=""
fi

for ref in $(yq '[.contacts[]?.ref] + [.conversations[]?.with[]?] | unique | .[]' "$res"); do
  grep -qx -- "$ref" <<<"$keys" || report "contact '$ref' is not a key in $contacts"
done

org_res="$org/resources.yaml"
if [[ -f "$org_res" ]]; then
  org_convs="$(yq '[.conversations[]?.id] + [.messaging[]?.channels[]?.id] | .[]' "$org_res")"
  for r in $(yq '.conversations[]? | select(has("ref")) | .ref' "$res"); do
    grep -qx -- "$r" <<<"$org_convs" || report "conversation ref '$r' is not an id in $org_res"
  done
fi

convs="$(yq '.conversations[]? | select(has("id")) | .id' "$res")"
for c in $(yq '.threads[]?.conversation' "$res"); do
  grep -qx -- "$c" <<<"$convs" || report "thread conversation '$c' is not a conversation id in $res"
done

for f in "$res" "$contacts"; do
  [[ -f "$f" ]] || continue
  # E.164 or formatted numbers; bare 10-digit runs are usually ids (page, tool, node) and pass
  perl -ne 'print "$.:$_" if /(?<![\w\/])\+\d{10,15}(?!\d)|(?<![\w\/])\(?[2-9]\d{2}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)/' "$f" \
    | sed "s|^|FAIL: phone-like value in $f:|" | grep . && fail=1 || true
  grep -nE '/Users/[a-z]|/home/[a-z]' "$f" | sed "s|^|FAIL: home path in $f:|" | grep . && fail=1 || true
  # a key-like value: 20+ token chars with both a letter and a digit (names like app/prod pass)
  perl -ne 'print "$.:$_" if /(api[_-]?key|secret|token|password)["\x27]?\s*[:=]\s*["\x27]?(?=[A-Za-z0-9_\-]*\d)(?=[A-Za-z0-9_\-]*[A-Za-z])[A-Za-z0-9_\-]{20,}/i' "$f" \
    | sed "s|^|FAIL: key-like value in $f:|" | grep . && fail=1 || true
done

[[ $fail -eq 0 ]] && echo "ok: $res"
exit $fail
