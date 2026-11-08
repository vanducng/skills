#!/usr/bin/env bash
# --options writes 2+ distinct options and one pick to the record's reports/.
set -u
f=.workbench/price-cache/reports/options.md
[ -f "$f" ] || { echo "no $f"; exit 1; }
[ "$(grep -Ec '^## Option' "$f")" -ge 2 ] || { echo "fewer than 2 options"; exit 1; }
grep -Eq '^Pick: Option [A-Z]' "$f" || { echo "no 'Pick: Option X' line"; exit 1; }
echo ok
