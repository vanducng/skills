#!/bin/sh
# The new post continues the toolkit series (one new file under source/_posts with series: toolkit-diary) and names
# no client org, project, host or person from the records.
new=$(cd blog/source/_posts && ls | grep -vxE '2026-02-20-toolkit-diary-1.md|2026-02-27-toolkit-diary-2.md|2026-02-25-garden.md')
[ "$(printf '%s\n' "$new" | grep -c .)" -eq 1 ] || { echo "want exactly one new post, got: $new"; exit 1; }
f="blog/source/_posts/$new"
awk 'NR==1&&/^---$/{fm=1;next} fm&&/^---$/{exit} fm' "$f" | grep -qE '^series:[[:space:]]*"?toolkit-diary"?[[:space:]]*$' || { echo "no series: toolkit-diary in the front matter"; exit 1; }
grep -qiE 'json|envelope' "$f" || { echo "misses the week's fact"; exit 1; }
if grep -inE '(^|[^a-z0-9])(northwind|ledger|priya|raman|build-box-7)([^a-z0-9-]|$)' "$f"; then echo "names a private name"; exit 1; fi
