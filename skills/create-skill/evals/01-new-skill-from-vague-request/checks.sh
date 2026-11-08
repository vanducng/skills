#!/usr/bin/env bash
# A new skill exists with a routed description, a short body, 3+ evals (one clean), and the repo validator passes.
python3 - <<'PY'
import json, pathlib, re, sys
root = pathlib.Path("skills")
new = [p for p in sorted(root.iterdir()) if p.is_dir() and p.name != "sample"]
if not new:
    sys.exit("no new skill directory")
skill = new[0]
text = (skill / "SKILL.md").read_text()
m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.S)
if not m:
    sys.exit("no frontmatter")
front, body = m.group(1), m.group(2)
if not re.search(rf"^name:\s*{re.escape(skill.name)}\s*$", front, re.M):
    sys.exit("name does not equal the directory")
desc = re.search(r"^description:\s*(.+?)(?=^\w[\w-]*:|\Z)", front, re.M | re.S).group(1).strip().strip('"').lower()
if "release notes" not in desc or "draft release notes" not in desc:
    sys.exit("description lacks the literal trigger phrases")
if len(desc) > 1024:
    sys.exit("description too long")
words = len(body.split())
if words > 800:
    sys.exit(f"body is {words} words, over the 800 ceiling")
scenarios = [d for d in (skill / "evals").glob("*/") if d.is_dir()] if (skill / "evals").is_dir() else []
if len(scenarios) < 3:
    sys.exit(f"{len(scenarios)} eval scenarios, need 3")
for d in scenarios:
    if not (d / "prompt.md").is_file() or not (d / "checks.sh").is_file():
        sys.exit(f"{d.name}: needs prompt.md and checks.sh")
clean = 0
for d in scenarios:
    meta = d / "scenario.json"
    if meta.is_file() and json.loads(meta.read_text()).get("clean") is True:
        clean += 1
if not clean:
    sys.exit("no clean case (scenario.json with clean: true)")
PY
[ $? -eq 0 ] || exit 1
bash scripts/validate.sh
