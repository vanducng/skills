#!/usr/bin/env bash
# check-release-versions.sh — ensure skill catalog release versions stay in sync.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - "$REPO" <<'PY'
import json
import pathlib
import re
import sys
import tomllib

repo = pathlib.Path(sys.argv[1])
semver = re.compile(
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)

version_txt = (repo / "version.txt").read_text(encoding="utf-8").strip()
plugin = json.loads((repo / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
marketplace = json.loads((repo / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
skills = tomllib.loads((repo / "skills.toml").read_text(encoding="utf-8"))

market_versions = [
    item.get("version", "")
    for item in marketplace.get("plugins", [])
    if item.get("name") == "vd"
]
values = {
    "version.txt": version_txt,
    "skills.toml targets.claude.bundle.version": (
        skills.get("targets", {})
        .get("claude", {})
        .get("bundle", {})
        .get("version", "")
    ),
    ".claude-plugin/plugin.json version": plugin.get("version", ""),
    ".claude-plugin/marketplace.json plugins[name=vd].version": (
        market_versions[0] if len(market_versions) == 1 else ""
    ),
}

errors = []
if len(market_versions) != 1:
    errors.append("expected exactly one marketplace plugin named 'vd'")
for label, value in values.items():
    if not value:
        errors.append(f"{label} is missing")
    elif not semver.match(value):
        errors.append(f"{label} is not valid SemVer: {value!r}")

unique = set(values.values())
if len(unique) != 1:
    errors.append("release versions differ:")
    for label, value in values.items():
        errors.append(f"  {label}: {value}")

if errors:
    print("release version check failed", file=sys.stderr)
    for error in errors:
        print(error, file=sys.stderr)
    sys.exit(1)

print(f"OK release versions {version_txt}")
PY
