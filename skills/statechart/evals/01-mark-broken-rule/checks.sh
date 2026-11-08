#!/usr/bin/env bash
# The model must break the rule (the late webhook charges a cancelled order) and the chart must mark where.
. "$(dirname "$0")/../common-checks.sh"
grep -E '^## .+ breaks$' "$report" | grep -Evq '^## (NoDeadlock|CHECK_DEADLOCK) breaks$' \
  || { echo "the report names no broken rule other than a deadlock"; exit 1; }
grep -Eq '^ *class s[0-9]+ (breaks|mayBreak)$' "$chart" || { echo "the chart marks no state that breaks a rule"; exit 1; }
echo ok
