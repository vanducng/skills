#!/usr/bin/env bash
# Tests for rig-kind.cjs. Run: bash skills/openrig-workspace/scripts/rig-kind.test.sh
# With PROJECTS_ROOT set (and yq), each kind's seats are also compared with its template's pod members.
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$DIR/rig-kind.cjs"
pass=0
fail=0
ok()  { pass=$((pass+1)); echo "  ✓ $1"; }
bad() { fail=$((fail+1)); echo "  ✗ $1"; }

field() { node "$RUNNER" "$@" --json | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const r=JSON.parse(s);console.log(process.argv[1]==="seats"?r.seats.map(x=>x.id).sort().join(" "):r[process.argv[1]])})' "${FIELD}"; }
expect() {
  local desc="$1" want="$2"; shift 2
  local got; got="$(field "$@" 2>&1)"
  [[ "$got" == "$want" ]] && ok "$desc" || bad "$desc (got '$got', want '$want')"
}

echo "kind to template"
FIELD=template
expect "feature low runs solo" solo --kind feature --profile low
expect "feature medium runs workshop" workshop --kind feature --profile medium
expect "feature high runs factory" factory --kind feature --profile high
expect "bugfix runs workshop" workshop --kind bugfix
expect "sop runs solo" solo --kind sop
expect "content runs studio" studio --kind content

echo "seat ids use the pod.member names"
FIELD=seats
SOLO="dev.build"
STUDIO="research.writer"
WORKSHOP="dev.build dev.qa dev.review orch.human orch.lead"
FACTORY="dev.build dev.design dev.qa orch.advisor orch.human orch.lead orch.pm review.r1"
expect "solo" "$SOLO" --kind feature --profile low
expect "workshop" "$WORKSHOP" --kind feature --profile medium
expect "factory" "$FACTORY" --kind feature --profile high
expect "bugfix has the workshop seats" "$WORKSHOP" --kind bugfix
expect "sop has the solo seat" "$SOLO" --kind sop
expect "content has the writer seat" "$STUDIO" --kind content

echo "slice template and the second reviewer"
FIELD=sliceTemplate
expect "bugfix keeps the bug-fix slice template" bug-fix --kind bugfix
expect "content keeps the placeholder slice template" placeholder --kind content
FIELD=rule
got="$(field --kind feature --profile high)"
[[ "$got" == *"rig add"* && "$got" == *"review.r2"* ]] && ok "factory says review.r2 is added with rig add" || bad "factory rule: $got"

echo "every seat names a role or the terminal"
roles="$(node "$RUNNER" --list --json | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{console.log([...new Set(JSON.parse(s).flatMap(r=>r.seats.map(x=>x.model)))].sort().join(" "))})')"
[[ "$roles" == "advisor build design lead pm qa review terminal writer" ]] && ok "roles: $roles" || bad "roles: $roles"

echo "refusals"
refuse() {
  local desc="$1" frag="$2"; shift 2
  local out code; out="$(node "$RUNNER" "$@" 2>&1)"; code=$?
  [[ $code != 0 && "$out" == *"$frag"* ]] && ok "$desc" || bad "$desc (exit $code: $out)"
}
refuse "no kind" "Pass --kind"
refuse "feature without a profile" "requires --profile" --kind feature
refuse "an unknown profile" "Unknown --profile" --kind feature --profile huge
refuse "a profile on bugfix" "does not take --profile" --kind bugfix --profile low
refuse "a profile on content" "does not take --profile" --kind content --profile low
refuse "an unknown kind" "Unknown --kind" --kind chore

if [[ -n "${PROJECTS_ROOT:-}" && -d "$PROJECTS_ROOT/specs/rigs" ]] && command -v yq >/dev/null; then
  echo "seats match the templates in \$PROJECTS_ROOT/specs/rigs"
  for t in solo workshop factory studio; do
    file="$PROJECTS_ROOT/specs/rigs/$t/rig.yaml"
    if [[ ! -f "$file" ]]; then bad "$t: no $file"; continue; fi
    have="$(yq '.pods[] as $p | $p.members[] | $p.id + "." + .id' "$file" | sort | tr '\n' ' ' | sed 's/ $//')"
    case $t in solo) want="$SOLO" ;; workshop) want="$WORKSHOP" ;; factory) want="$FACTORY" ;; studio) want="$STUDIO" ;; esac
    [[ "$have" == "$want" ]] && ok "$t template has the same seats" || bad "$t: template has '$have'"
  done
else
  echo "  - PROJECTS_ROOT or yq not set: template comparison skipped"
fi

echo
echo "$pass passed, $fail failed"
[[ "$fail" == 0 ]]
