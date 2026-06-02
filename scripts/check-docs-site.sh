#!/usr/bin/env bash
# check-docs-site.sh - mechanical score/check for the Zensical docs site.
set -euo pipefail

MODE="${1:---check}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - "$MODE" "$REPO" <<'PY'
import pathlib
import re
import sys
import tomllib

mode = sys.argv[1]
repo = pathlib.Path(sys.argv[2])

def text(rel):
    path = repo / rel
    return path.read_text(encoding="utf-8") if path.exists() else ""

def exists(rel):
    return (repo / rel).exists()

zensical = tomllib.loads(text("zensical.toml")) if exists("zensical.toml") else {}
project = zensical.get("project", {})
nav = project.get("nav", [])

checks = [
    ("zensical config exists", exists("zensical.toml")),
    ("site_url is custom domain", project.get("site_url") == "https://skills.vanducng.dev/"),
    ("site_dir is site", project.get("site_dir") == "site"),
    ("custom css configured", "stylesheets/skills.css" in project.get("extra_css", [])),
    ("navigation has at least four sections", len(nav) >= 4),
    ("homepage exists", exists("docs/index.md")),
    ("install guide exists", exists("docs/install.md")),
    ("canonical docs exist", all(exists(p) for p in [
        "docs/development-guidelines.md",
        "docs/system-architecture.md",
        "docs/tech-stack.md",
        "docs/deployment.md",
    ])),
    ("architecture visual exists", exists("docs/assets/architecture.svg")),
    ("stylesheet has hero and cards", ".vd-hero" in text("docs/stylesheets/skills.css") and ".vd-card-grid" in text("docs/stylesheets/skills.css")),
    ("homepage hides unused left sidebar", "body:has(.vd-hero) .md-sidebar--primary" in text("docs/stylesheets/skills.css") and "display: none;" in text("docs/stylesheets/skills.css")),
    ("homepage uses aligned content rail", "body:has(.vd-hero) .md-main__inner" in text("docs/stylesheets/skills.css") and "max-width: 61rem;" in text("docs/stylesheets/skills.css")),
    ("old journal docs removed", not exists("docs/journals/2026-05-05-vd-cli-shipped.md")),
    ("pages workflow uses zensical", "zensical build --clean --strict" in text(".github/workflows/pages.yml")),
    ("pages workflow writes CNAME", "skills.vanducng.dev" in text(".github/workflows/pages.yml") and "site/CNAME" in text(".github/workflows/pages.yml")),
    ("pages workflow no stale tools path", "tools/vd/docs" not in text(".github/workflows/pages.yml")),
    ("README links public docs", "https://skills.vanducng.dev" in text("README.md")),
    ("install docs use v2 go path", "github.com/vanducng/vd-cli/v2/cmd/vd@latest" in text("docs/install.md")),
    ("install docs cover codex", "vd install codex --scope repo" in text("docs/install.md")),
    ("install docs cover claude dev", "vd install claude --dev" in text("docs/install.md")),
    ("install docs avoid unshipped windows arm asset", "vd_windows_arm64.zip" not in text("docs/install.md")),
    ("llms canonical exists", exists("docs/llms.txt") and text("docs/llms.txt").startswith("# vd skills\n")),
    ("llms full context exists", exists("docs/llms-full.txt") and "vd install codex --scope repo" in text("docs/llms-full.txt")),
    ("llm singular pointer exists", exists("docs/llm.txt") and "https://skills.vanducng.dev/llms.txt" in text("docs/llm.txt")),
    ("robots advertises llms", exists("docs/robots.txt") and "LLMs: https://skills.vanducng.dev/llms.txt" in text("docs/robots.txt")),
    ("agent context page exists", exists("docs/agent-context.md") and "/llms.txt" in text("docs/agent-context.md")),
    ("skill-management uses v2 go path", "github.com/vanducng/vd-cli/cmd/vd@latest" not in text("skills/skill-management/SKILL.md")),
    ("zensical skill exists", exists("skills/zensical/SKILL.md")),
]

passed = sum(1 for _, ok in checks if ok)
score = round(passed * 100 / len(checks))

if mode == "--score":
    print(score)
    sys.exit(0)

for name, ok in checks:
    print(f"{'OK  ' if ok else 'FAIL'} {name}")
print(f"score={score}")

if mode != "--check":
    print(f"unknown mode: {mode}", file=sys.stderr)
    sys.exit(2)
if passed != len(checks):
    sys.exit(1)
PY
