#!/usr/bin/env bash
# An investigation is proved by cited claims, each labelled measured, inferred or guess.
. "$(dirname "$0")/../common-checks.sh"
type_is 'investigation'
grep -Eiq '^- \[ \] .*file:line' "$spec" || { echo "contract does not ask for file:line citations"; exit 1; }
grep -Eiq '^- \[ \] .*measured.*inferred.*guess' "$spec" || { echo "contract does not label claims measured/inferred/guess"; exit 1; }
echo ok
