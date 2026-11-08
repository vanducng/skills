#!/usr/bin/env bash
# A correct change: both axes pass and nothing Important is open.
. "$(dirname "$0")/../common-checks.sh"
[ "$(axis spec)" = pass ] && [ "$(axis standards)" = pass ] || { echo "axes are spec=$(axis spec) standards=$(axis standards), want pass/pass"; exit 1; }
[ "$(open_important spec)" -eq 0 ] && [ "$(open_important standards)" -eq 0 ] || { echo "an Important finding is open on a correct change"; exit 1; }
echo ok
