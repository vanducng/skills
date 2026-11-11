#!/bin/sh
# A one-off number is a query, not a dashboard: the answer, and no question sheet or dashboard files.
. "$(dirname "$0")/../common.sh"
grep -Eq '(^|[^0-9])216([^0-9]|$)' "$EVAL_OUTPUT" || { echo "the answer (216) is not in the reply"; exit 1; }
made=$(new_files | grep -Ei '\.(md|csv|html?|png|svg|ya?ml|json)$')
[ -z "$made" ] || { echo "started the dashboard flow: $made"; exit 1; }
! grep -Eiq 'question sheet|field map|mockup' "$EVAL_OUTPUT" || { echo "the reply starts the dashboard flow"; exit 1; }
echo ok
