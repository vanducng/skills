#!/usr/bin/env bash
# Mini-requirement 2 (the stranger) is missing: Spec fails with an open Important finding on the spec axis.
. "$(dirname "$0")/../common-checks.sh"
[ "$(axis spec)" = fail ] || { echo "spec axis is '$(axis spec)', want fail"; exit 1; }
[ "$(open_important spec)" -ge 1 ] || { echo "no open Important finding on the spec axis"; exit 1; }
echo ok
