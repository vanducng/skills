#!/usr/bin/env bash
# --options writes 2+ distinct options, a Read: line, a Red flags: line and one pick to the record's reports/.
set -u
f=.workbench/price-cache/reports/options.md
[ -f "$f" ] || { echo "no $f"; exit 1; }
[ "$(grep -Ec '^## Option' "$f")" -ge 2 ] || { echo "fewer than 2 options"; exit 1; }
grep -Eq '^Pick: Option [A-Z]' "$f" || { echo "no 'Pick: Option X' line"; exit 1; }
grep -Eq '^Read: .+' "$f" || { echo "no 'Read:' line (the systems grounded on)"; exit 1; }
grep -Eq '^Red flags: .+' "$f" || { echo "no 'Red flags:' line"; exit 1; }
echo ok
