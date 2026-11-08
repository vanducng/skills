# Sourced by checks.sh: exactly one new record, with intent, a type, numbered mini-requirements and a checkbox contract.
set -u
n=$(find .workbench -name SPEC.md 2>/dev/null | wc -l | tr -d ' ')
[ "$n" = 1 ] || { echo "want exactly one .workbench/<id>/SPEC.md, found $n"; exit 1; }
spec=$(find .workbench -name SPEC.md)
grep -Eq '^intent: *"?[A-Za-z].{10,}' "$spec" || { echo "no restated intent in $spec"; exit 1; }
grep -Eq '^[0-9]+\. .+' "$spec" || { echo "no numbered mini-requirement"; exit 1; }
grep -Eq '^- \[ \] .+' "$spec" || { echo "no checkbox proof contract line"; exit 1; }
! grep -qi 'TODO' "$spec" || { echo "TODO left in $spec"; exit 1; }
type_is() { grep -Eiq "^type: *\"?($1)" "$spec" || { echo "type is '$(grep -m1 '^type:' "$spec")', want $1"; exit 1; }; }
