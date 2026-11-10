#!/bin/sh
# Reconciliation against the reference: the orders tile is 8% short, which fails a stated tolerance.
. "$(dirname "$0")/../common.sh"
said > "$T/said"
# A tolerance is stated in a sentence ("outside the 1% tolerance") or as a table column whose row holds a percentage.
in_table=$(awk -F'|' 'tolower($0) ~ /toleran/ { for (i = 1; i <= NF; i++) if (tolower($i) ~ /toleran/) col = i; next }
  col && $col ~ /[0-9.]+ ?%/ { print "yes"; exit }' "$T/said")
grep -Eiq 'toleran[a-z]*[^.]*[0-9.]+ ?%|[0-9.]+ ?%[^.]*toleran' "$T/said" || [ -n "$in_table" ] \
  || { echo "no tolerance stated (a percentage next to the word tolerance, or in a Tolerance column)"; exit 1; }
grep -Eq '(^|[^0-9.])8(\.0+|\.7[0-9]*)? ?%' "$T/said" || { echo "the 8% gap on the orders tile is not stated"; exit 1; }
grep -Eiq 'not ready|fail|does not reconcile|doesn.t reconcile|outside (the |our |a )?toleran|do not publish|don.t publish|not (yet )?publish|block' "$T/said" \
  || { echo "the orders gap is not called a failure"; exit 1; }
echo ok
