#!/usr/bin/env bash
# The spec is met and REVIEW.md has no comment rule, but the diff leaves the header comment stale (3 tries, 100 ms)
# and adds "// wait", which restates the next line: standards fails with an open Important finding, spec passes.
. "$(dirname "$0")/../common-checks.sh"
[ "$(axis standards)" = fail ] || { echo "standards axis is '$(axis standards)', want fail (stale and restating comments)"; exit 1; }
[ "$(axis spec)" = pass ] || { echo "spec axis is '$(axis spec)', want pass (the spec is met)"; exit 1; }
[ "$(open_important standards)" -ge 1 ] || { echo "no open Important finding on the standards axis"; exit 1; }
grep -qiE 'comment' "$v" || { echo "the verdict never names the comment"; exit 1; }
echo ok
