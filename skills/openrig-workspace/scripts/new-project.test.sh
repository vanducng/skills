#!/usr/bin/env bash
# Tests for new-project.cjs on a synthetic workspace root. Run: bash skills/openrig-workspace/scripts/new-project.test.sh
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$DIR/new-project.cjs"
pass=0
fail=0
ok()  { pass=$((pass+1)); echo "  ✓ $1"; }
bad() { fail=$((fail+1)); echo "  ✗ $1"; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ROOT="$TMP/ws"
mkdir -p "$ROOT/orgs/acme/projects/shop" "$ROOT/fleet"
cat > "$ROOT/workspace.yaml" <<'YAML'
schema: openrig.workspace/v0alpha1
projects:
  - id: acme.shop
    root: orgs/acme/projects/shop
    rigs: [shop]
YAML
printf 'schema: projects.org/v1\nid: acme\nname: Acme\n' > "$ROOT/orgs/acme/org.yaml"
printf 'schema: projects.resources/v2\n' > "$ROOT/orgs/acme/resources.yaml"
printf 'schema: projects.contacts/v1\norg: acme\ncontacts: {}\n' > "$ROOT/orgs/acme/contacts.yaml"
cat > "$ROOT/fleet/machines.yaml" <<'YAML'
schema: projects.machines/v1
standard:
  skills: ~/skills
machines:
  box-a:
    default: true
  box-b:
    ssh_alias: b
YAML

run() { node "$RUNNER" "$@" 2>&1; }
snapshot() { (cd "$ROOT" && find . -type f | sort | xargs cksum) ; }

echo "creates a project"
if ! command -v yq >/dev/null; then echo "  - yq not installed: the check-resources.sh step cannot run"; exit 2; fi
out="$(run acme billing --host box-b --root "$ROOT")"; code=$?
[[ $code == 0 ]] && ok "exit 0 (check-resources.sh passed)" || bad "exit $code: $out"
grep -q "^ok: .*orgs/acme/projects/billing/resources.yaml" <<<"$out" && ok "check-resources.sh ran on the new project" || bad "no check output: $out"
P="$ROOT/orgs/acme/projects/billing"
for f in AGENTS.md SPEC.md project.yaml repos.yaml resources.yaml missions/.gitkeep; do
  [[ -e "$P/$f" ]] && ok "wrote $f" || bad "missing $f"
done
grep -q '^host: box-b$' "$P/repos.yaml" && ok "repos.yaml carries the host" || bad "host not in repos.yaml"
grep -q 'id: acme.billing' "$P/project.yaml" && ok "project.yaml id is <org>.<project>" || bad "project id"
grep -q '^intent: "' "$P/SPEC.md" && ok "SPEC.md has an intent" || bad "no intent"
yq '.projects[].id' "$ROOT/workspace.yaml" | tr '\n' ' ' | grep -q 'acme.shop acme.billing' && ok "workspace.yaml lists it after the existing project" || bad "workspace.yaml: $(cat "$ROOT/workspace.yaml")"
[[ "$(yq '.projects[] | select(.id == "acme.billing") | .root' "$ROOT/workspace.yaml")" == "orgs/acme/projects/billing" ]] && ok "workspace.yaml root is right" || bad "workspace root"
[[ "$(yq '.projects[0].rigs[0]' "$ROOT/workspace.yaml")" == "shop" ]] && ok "existing entries untouched" || bad "existing entry changed"
bash "$DIR/check-resources.sh" "$P" >/dev/null && ok "check-resources.sh passes on its own" || bad "check-resources.sh fails"

echo "intent option round-trips through YAML"
n=0
intent_case() {
  local desc="$1" text="$2" want="${3:-$2}" name got
  n=$((n+1)); name="intent$n"
  node "$RUNNER" acme "$name" --host box-a --intent "$text" --root "$ROOT" >/dev/null 2>&1; code=$?
  got="$(sed -n '/^---$/,/^---$/p' "$ROOT/orgs/acme/projects/$name/SPEC.md" | sed '1d;$d' | yq '.intent' 2>&1)"
  if [[ $code == 0 && "$got" == "$want" ]]; then ok "$desc"; else bad "$desc (exit $code, parsed '$got', want '$want')"; fi
}
intent_case "a backslash" 'path C:\quux\bar'
intent_case "a double quote" 'Ship "refunds" in one go'
intent_case "a colon and a hash" 'Goal: ship it # now'
intent_case "a single quote" "It's the one"
intent_case "a newline becomes a space" $'first line\nsecond line' 'first line second line'
intent_case "unicode" 'Café and 日本語'
intent_case "a leading dash and brackets" '- [x] {y}'

echo "refusals (nothing is written)"
before="$(snapshot)"
refuse() {
  local desc="$1" pattern="$2"; shift 2
  local out code
  out="$(run "$@")"; code=$?
  if [[ $code != 0 && "$out" == *"$pattern"* ]]; then ok "$desc"; else bad "$desc (exit $code: $out)"; fi
}
refuse "a second run on the same project" "already exists" acme billing --host box-a --root "$ROOT"
refuse "an existing project in workspace.yaml" "already exists" acme shop --host box-a --root "$ROOT"
refuse "--help as a name" "option" --help billing2 --host box-a --root "$ROOT"
refuse "--help in the project position" "option" acme --help --host box-a --root "$ROOT"
refuse "a name starting with a dash" "option" acme -x --host box-a --root "$ROOT"
refuse "an uppercase name" "invalid project name" acme Billing --host box-a --root "$ROOT"
refuse "a name with a slash" "invalid project name" acme a/b --host box-a --root "$ROOT"
refuse "a name with two dashes in a row" "invalid project name" acme a--b --host box-a --root "$ROOT"
refuse "an invalid org name" "invalid org name" "ac me" x --host box-a --root "$ROOT"
refuse "an org that does not exist" "does not exist" nope x --host box-a --root "$ROOT"
refuse "a missing host" "--host" acme x2 --root "$ROOT"
refuse "an unknown host" "unknown host 'box-z'" acme x3 --host box-z --root "$ROOT"
refuse "an option without a value" "needs a value" acme x4 --host --root "$ROOT"
refuse "one name only" "give <org> and <project>" acme --host box-a --root "$ROOT"
refuse "a root without workspace.yaml" "no workspace.yaml" acme x5 --host box-a --root "$TMP"
[[ "$(snapshot)" == "$before" ]] && ok "no refusal changed any file" || bad "a refused run wrote files"

echo "machines.yaml in another indent and quoting"
cat > "$ROOT/fleet/machines.yaml" <<'YAML'
schema: projects.machines/v1
machines:
    "box-q":
        default: true
    box-r: {ssh_alias: r}
YAML
out="$(run acme fourspace --host box-q --root "$ROOT")"; [[ $? == 0 ]] && ok "a quoted key at four-space indent is a machine" || bad "four-space: $out"
out="$(run acme flowmap --host box-r --root "$ROOT")"; [[ $? == 0 ]] && ok "a key with a flow mapping is a machine" || bad "flow map: $out"
refuse "a host not in the re-indented file" "unknown host 'box-a'" acme x6 --host box-a --root "$ROOT"

echo "a workspace.yaml without a projects: list refuses before writing"
BAD="$TMP/bad"
mkdir -p "$BAD/orgs/acme"
cp "$ROOT/orgs/acme/"*.yaml "$BAD/orgs/acme/"
printf 'schema: openrig.workspace/v0alpha1\nproject:\n  - id: acme.shop\n' > "$BAD/workspace.yaml"
before_bad="$( (cd "$BAD" && find . -type f | sort | xargs cksum) )"
refuse "no projects: list" "no block projects: list" acme half --host x --root "$BAD"
[[ ! -e "$BAD/orgs/acme/projects/half" ]] && ok "no project dir was created" || bad "half-created project left behind"
[[ "$( (cd "$BAD" && find . -type f | sort | xargs cksum) )" == "$before_bad" ]] && ok "no file changed" || bad "a file changed"

echo "without fleet/machines.yaml the host is accepted with a warning"
rm "$ROOT/fleet/machines.yaml"
out="$(run acme loose --host anything --root "$ROOT")"; code=$?
[[ $code == 0 && "$out" == *"warning: no fleet/machines.yaml"* ]] && ok "warns and creates" || bad "exit $code: $out"

echo "root from PROJECTS_ROOT and from the working directory"
out="$(PROJECTS_ROOT="$ROOT" run acme viaenv --host x)"; [[ $? == 0 ]] && ok "PROJECTS_ROOT" || bad "PROJECTS_ROOT: $out"
out="$(cd "$ROOT/orgs/acme" && node "$RUNNER" acme viacwd --host x 2>&1)"; [[ $? == 0 ]] && ok "found workspace.yaml above the cwd" || bad "cwd: $out"

echo
echo "$pass passed, $fail failed"
[[ "$fail" == 0 ]]
