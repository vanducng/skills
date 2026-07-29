#!/usr/bin/env bash
# check-docs-site.sh - mechanical score/check for the Astro Starlight docs site.
set -euo pipefail

MODE="${1:---check}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - "$MODE" "$REPO" <<'PY'
import pathlib
import re
import sys

mode = sys.argv[1]
repo = pathlib.Path(sys.argv[2])

def text(rel):
    path = repo / rel
    return path.read_text(encoding="utf-8") if path.exists() else ""

def exists(rel):
    return (repo / rel).exists()

def first_int(pattern, body):
    m = re.search(pattern, body)
    return int(m.group(1)) if m else None

cfg = text("docs/astro.config.mjs")
pkg = text("docs/package.json")
pages = text(".github/workflows/pages.yml")
install = text("docs/content/install.md")
skills_page = text("docs/content/skills.md")
home = text("docs/content/index.mdx")
agent_ctx = text("docs/content/agent-context.md")
dev_guidelines = text("docs/content/development-guidelines.md")
readme = text("README.md")
theme = text("docs/src/styles/theme.css")
shared_theme = text("skills/tech-docs/assets/theme.css")

skill_dirs = sorted(
    p.name for p in (repo / "skills").iterdir()
    if p.is_dir() and (p / "SKILL.md").exists()
)
skill_count = len(skill_dirs)

checks = [
    # Site wiring (Astro Starlight)
    ("astro config exists", exists("docs/astro.config.mjs")),
    ("site is custom domain", "site: 'https://skills.vanducng.dev'" in cfg),
    ("starlight integration configured", "@astrojs/starlight" in pkg and "starlight(" in cfg),
    ("llms.txt plugin configured", "starlight-llms-txt" in cfg and "starlight-llms-txt" in pkg),
    ("custom theme css configured", "customCss: ['./src/styles/theme.css']" in cfg and exists("docs/src/styles/theme.css")),
    ("site title offset targets link only", ".title-wrapper > .site-title" in theme and ".title-wrapper {\n    transform" not in theme),
    ("shared theme title offset targets link only", ".title-wrapper > .site-title" in shared_theme and ".title-wrapper {\n    transform" not in shared_theme),
    ("site search width targets trigger only", "site-search > button" in theme and "site-search button" not in theme),
    ("shared theme search width targets trigger only", "site-search > button" in shared_theme and "site-search button" not in shared_theme),
    ("CNAME is custom domain", text("docs/public/CNAME").strip() == "skills.vanducng.dev"),

    # Canonical content pages
    ("homepage exists", exists("docs/content/index.mdx")),
    ("install guide exists", exists("docs/content/install.md")),
    ("getting started guide exists", exists("docs/content/getting-started.md")),
    ("canonical project docs exist", all(exists(p) for p in [
        "docs/content/development-guidelines.md",
        "docs/content/tech-stack.md",
        "docs/content/deployment.md",
    ])),
    ("catalog page exists", exists("docs/content/skills.md")),
    ("workflows page exists", exists("docs/content/workflows.md")),
    ("agent context page exists", exists("docs/content/agent-context.md") and "/llms.txt" in agent_ctx),

    # Agent / LLM plain-text entry points
    ("llm singular pointer exists", exists("docs/public/llm.txt") and "https://skills.vanducng.dev/llms.txt" in text("docs/public/llm.txt")),
    ("robots advertises llms", exists("docs/public/robots.txt") and "LLMs: https://skills.vanducng.dev/llms.txt" in text("docs/public/robots.txt")),

    # Install content contract
    ("install docs use v2 go path", "github.com/vanducng/vd-cli/v2/cmd/vd@latest" in install),
    ("install docs cover codex", "vd install codex --scope repo" in install),
    ("install docs cover claude dev", "vd install claude --dev" in install),
    ("install docs avoid unshipped windows arm asset", "vd_windows_arm64.zip" not in install),

    # Deployment
    ("pages workflow builds with astro", "withastro/action" in pages and "path: ./docs" in pages),
    ("README links public docs", "https://skills.vanducng.dev" in readme),

    # Docs track the skills/ catalog
    ("catalog page count matches skills dir", first_int(r"contains (\d+) skills", skills_page) == skill_count),
    ("homepage count matches skills dir", first_int(r"(\d+) skills across", home) == skill_count),

    # Zensical fully removed (docs migrated to Astro Starlight)
    ("zensical config removed", not exists("zensical.toml")),
    ("no zensical references in catalog docs", not any(
        "zensical" in body.lower()
        for body in (skills_page, agent_ctx, dev_guidelines)
    )),
]

passed = sum(1 for _, ok in checks if ok)
score = round(passed * 100 / len(checks))

if mode == "--score":
    print(score)
    sys.exit(0)

for name, ok in checks:
    print(f"{'OK  ' if ok else 'FAIL'} {name}")
print(f"skills={skill_count} score={score}")

if mode != "--check":
    print(f"unknown mode: {mode}", file=sys.stderr)
    sys.exit(2)
if passed != len(checks):
    sys.exit(1)
PY
