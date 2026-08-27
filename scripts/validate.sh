#!/usr/bin/env bash
# validate.sh — lint frontmatter for every skills/*/SKILL.md and repo skill-call conventions.
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
if desc[0] in "'\"" and desc[-1] == desc[0] and len(desc) > 1:
    desc = desc[1:-1]
if len(desc) > 1024:
    print(f"'description' exceeds 1024 characters ({len(desc)})"); sys.exit(1)

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

prefix_result="$(python3 - "$REPO" <<'PY'
import pathlib
import re
import subprocess
import sys

repo = pathlib.Path(sys.argv[1])
root_args = ["AGENTS.md", "CHANGELOG.md", "README.md", "skills.toml", "skills"]
pattern = re.compile(r"(?<![\w/])(?:/|\$)(?:vd|ck):[a-z][a-z0-9-]*")
matches = []

def candidate_files():
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-co", "--exclude-standard", "--", *root_args],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        result = None

    if result is not None and result.returncode == 0:
        for rel in result.stdout.splitlines():
            path = repo / rel
            if path.is_file():
                yield path
        return

    for arg in root_args:
        root = repo / arg
        if root.is_file():
            yield root
        elif root.is_dir():
            for child in root.rglob("*"):
                if child.is_file():
                    yield child

for path in candidate_files():
    if ".git" in path.parts:
        continue
    rel = path.relative_to(repo)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for lineno, line in enumerate(text.splitlines(), 1):
        if pattern.search(line):
            matches.append(f"{rel}:{lineno}: {line.strip()}")

if matches:
    print("runtime-prefixed skill IDs found; use canonical IDs like `vd:cook` without slash or dollar invocation prefixes")
    for match in matches:
        print(match)
    sys.exit(1)

print("ok")
PY
)" || true

if [[ "$prefix_result" == "ok" ]]; then
  echo "OK   canonical skill IDs"
else
  echo "FAIL canonical skill IDs:"
  echo "$prefix_result"
  failed=$((failed + 1))
fi

echo
# Enforced: producer skills must write to the injected paths, not hardcoded umbrella paths.
if ! bash "${REPO}/scripts/check-skill-paths.sh" --enforce; then
  failed=$((failed + 1))
fi

echo
# Enforced: no em dashes or curly quotes in catalog prose (vd:unslop floor).
if ! bash "${REPO}/scripts/check-slop.sh" --enforce; then
  failed=$((failed + 1))
fi

[[ $failed -eq 0 ]]
