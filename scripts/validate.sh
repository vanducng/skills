#!/usr/bin/env bash
# validate.sh — lint frontmatter for every skills/*/SKILL.md.
# Asserts: file exists, frontmatter parses, name is kebab-case, name == basename(dir), description non-empty.
# Exit 0 if all pass, 1 if any fail.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_ROOT="${REPO}/skills"

[[ -d "$SKILLS_ROOT" ]] || { echo "no skills/ dir at $SKILLS_ROOT"; exit 0; }

failed=0
checked=0

for dir in "$SKILLS_ROOT"/*/; do
  [[ -d "$dir" ]] || continue
  dir="${dir%/}"
  name="$(basename "$dir")"
  skill_md="${dir}/SKILL.md"
  checked=$((checked + 1))

  if [[ ! -f "$skill_md" ]]; then
    echo "FAIL ${name}: missing SKILL.md"
    failed=$((failed + 1))
    continue
  fi

  result="$(python3 - "$skill_md" "$name" <<'PY'
import sys, re, pathlib

path = pathlib.Path(sys.argv[1])
expected_name = sys.argv[2]
text = path.read_text(encoding="utf-8")

# Extract frontmatter between the first two '---' lines.
m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
if not m:
    print("missing or malformed frontmatter (expected leading --- ... --- block)")
    sys.exit(1)

fm = m.group(1)
fields = {}
for line in fm.splitlines():
    if not line.strip() or line.lstrip().startswith("#"):
        continue
    if ":" not in line:
        continue
    k, _, v = line.partition(":")
    fields[k.strip()] = v.strip()

name = fields.get("name", "")
desc = fields.get("description", "")

if not name:
    print("missing 'name' in frontmatter"); sys.exit(1)
if not re.match(r"^[a-z][a-z0-9-]*$", name):
    print(f"'name' must be kebab-case, got: {name!r}"); sys.exit(1)
if name != expected_name:
    print(f"'name' ({name!r}) does not match directory ({expected_name!r})"); sys.exit(1)
if not desc:
    print("missing or empty 'description' in frontmatter"); sys.exit(1)

print("ok")
PY
  )" || true

  if [[ "$result" == "ok" ]]; then
    echo "OK   ${name}"
  else
    echo "FAIL ${name}: ${result}"
    failed=$((failed + 1))
  fi
done

echo
echo "summary: checked=${checked} failed=${failed}"
[[ $failed -eq 0 ]]
