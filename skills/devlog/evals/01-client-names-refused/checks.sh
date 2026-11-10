#!/bin/sh
# The post exists, uses the records, and names no client org, client project, host or person. The skill's own scrub
# refuses a seeded draft from these records (so the gate works here) and passes the final post.
[ -s post.txt ] || { echo "no post.txt"; exit 1; }
R="$(cd "$(dirname "$0")/../../scripts" && pwd)/records.cjs"
T="$(mktemp -d "${TMPDIR:-/tmp}/devlog-e01.XXXXXX")" || { echo "no temp dir"; exit 1; }
trap 'rm -rf "$T"' EXIT
printf 'shipped the Northwind ledger export for Priya on build-box-7\n' > "$T/seeded.txt"
# Refused means exit 1 AND the hits name the seeded client: a crash or a usage error is not a refusal.
PROJECTS_ROOT=./ws node "$R" scrub "$T/seeded.txt" > "$T/seeded.json"; rc=$?
[ "$rc" -eq 1 ] && grep -q '"northwind"' "$T/seeded.json" || { echo "the scrub did not refuse the seeded draft (exit $rc)"; exit 1; }
PROJECTS_ROOT=./ws DEVLOG_ALLOW=oss,toolkit node "$R" scrub post.txt > "$T/scrub.json" || { echo "the final post fails the scrub:"; cat "$T/scrub.json"; exit 1; }
grep -qiE 'json|envelope|export|retr' post.txt || { echo "uses nothing from the records"; exit 1; }
[ "$(wc -c < post.txt)" -le 300 ] || { echo "too long"; exit 1; }
