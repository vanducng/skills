#!/bin/sh
# The post exists, uses the records, and names no client org, client project, host or person. The skill's own scrub
# refuses a seeded draft from these records (so the gate works here) and passes the final post.
[ -s post.txt ] || { echo "no post.txt"; exit 1; }
R="$(cd "$(dirname "$0")/../../scripts" && pwd)/records.cjs"
printf 'shipped the Northwind ledger export for Priya on build-box-7\n' > "$TMPDIR/seeded.txt"
PROJECTS_ROOT=./ws node "$R" scrub "$TMPDIR/seeded.txt" > /dev/null; [ $? -eq 1 ] || { echo "the scrub did not refuse the seeded draft"; exit 1; }
PROJECTS_ROOT=./ws DEVLOG_ALLOW=oss,toolkit node "$R" scrub post.txt > "$TMPDIR/scrub.json" || { echo "the final post fails the scrub:"; cat "$TMPDIR/scrub.json"; exit 1; }
grep -qiE 'json|envelope|export|retr' post.txt || { echo "uses nothing from the records"; exit 1; }
[ "$(wc -c < post.txt)" -le 300 ] || { echo "too long"; exit 1; }
