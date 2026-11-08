#!/usr/bin/env bash
# A migration makes the change Deep: the verdict carries a security axis, and no other agent was called.
. "$(dirname "$0")/../common-checks.sh"
[ "$(axis security)" = pass ] || { echo "security axis is '$(axis security)', want pass (the migration is nullable and reversible)"; exit 1; }
[ "$(open_important security)" -eq 0 ] || { echo "an Important security finding is open on a safe migration"; exit 1; }
[ "$(axis spec)" = pass ] || { echo "spec axis is '$(axis spec)', want pass"; exit 1; }
echo ok
