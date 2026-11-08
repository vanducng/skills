#!/usr/bin/env bash
# A migration makes the change Deep: the verdict carries a security axis, and no other agent was called.
. "$(dirname "$0")/../common-checks.sh"
[ -n "$(axis security)" ] || { echo "no security axis on a Deep change"; exit 1; }
[ "$(axis spec)" = pass ] || { echo "spec axis is '$(axis spec)', want pass"; exit 1; }
echo ok
