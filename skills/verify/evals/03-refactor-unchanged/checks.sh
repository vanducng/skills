#!/usr/bin/env bash
# A behavior-preserving refactor: the same tests pass on both sides, and nothing is flagged.
. "$(dirname "$0")/../common-checks.sh"
[ "$(j outcome)" = same-pass ] || { echo "outcome is '$(j outcome)', want same-pass"; exit 1; }
echo ok
