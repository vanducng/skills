#!/usr/bin/env bash
# The fix is a script or lint the skill points at, not more prose.
python3 - <<'PY'
import os, pathlib, sys
skill = pathlib.Path("skills/changelog")
scripts = [p for p in (skill / "scripts").glob("*") if p.is_file() and p.stat().st_size > 0] if (skill / "scripts").is_dir() else []
if not scripts:
    sys.exit("no script under skills/changelog/scripts/")
text = (skill / "SKILL.md").read_text()
if not any(p.name in text for p in scripts):
    sys.exit("SKILL.md does not point at the script")
before = len((pathlib.Path(os.environ["EVAL_ORIG"]) / "skills/changelog/SKILL.md").read_text().split())
after = len(text.split())
if after > before + 60:
    sys.exit(f"SKILL.md grew from {before} to {after} words: that is more prose, not a fix")
PY
