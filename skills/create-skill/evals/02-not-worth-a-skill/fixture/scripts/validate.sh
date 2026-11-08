#!/usr/bin/env bash
# Minimal repo validator: every skills/*/SKILL.md has frontmatter, name == directory, description <= 1024 chars.
set -euo pipefail
python3 - <<'PY'
import pathlib, re, sys
bad = 0
for md in sorted(pathlib.Path("skills").glob("*/SKILL.md")):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", md.read_text(), re.S)
    if not m:
        print(f"FAIL {md}: no frontmatter"); bad += 1; continue
    name = re.search(r"^name:\s*(\S+)", m.group(1), re.M)
    desc = re.search(r"^description:\s*(.+?)(?=^\w[\w-]*:|\Z)", m.group(1), re.M | re.S)
    if not name or name.group(1) != md.parent.name:
        print(f"FAIL {md}: name must equal the directory"); bad += 1
    if not desc or len(desc.group(1).strip().strip('"')) > 1024:
        print(f"FAIL {md}: description missing or over 1024 chars"); bad += 1
sys.exit(1 if bad else 0)
PY
