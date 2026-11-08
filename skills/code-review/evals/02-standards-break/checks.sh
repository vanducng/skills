#!/usr/bin/env bash
# The spec is met but REVIEW.md rule 1 is broken: the axes are judged apart, standards fails and spec passes.
. "$(dirname "$0")/../common-checks.sh"
[ "$(axis standards)" = fail ] || { echo "standards axis is '$(axis standards)', want fail"; exit 1; }
[ "$(axis spec)" = pass ] || { echo "spec axis is '$(axis spec)', want pass (the spec is met)"; exit 1; }
[ "$(open_important standards)" -ge 1 ] || { echo "no open Important finding on the standards axis"; exit 1; }
echo ok
