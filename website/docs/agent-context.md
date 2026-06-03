---
title: "Agent Context"
---

This site publishes plain-text entry points for coding agents and LLM-powered tools.

## Canonical Files

| File | Purpose |
| --- | --- |
| [`/llms.txt`](llms.txt) | Curated root index: what this repo is, what to read first, and which docs are optional. |
| [`/llms-full.txt`](llms-full.txt) | Fuller single-file context with install, architecture, workflows, and skill taxonomy. |
| [`/llm.txt`](llm.txt) | Compatibility pointer for tools or users that try the singular spelling. |
| [`/sitemap.xml`](sitemap.xml) | Exhaustive generated site map for crawlers and search tools. |

## Recommended Agent Flow

1. Fetch `/llms.txt`.
2. Read the links under `## Core`.
3. Fetch `/llms-full.txt` only when a single larger context file is more useful than selective page fetches.
4. Prefer canonical skill IDs such as `vd:docs`, `vd:zensical`, and `vd:ship` when discussing skills.
5. Check source files in GitHub before making claims about implementation details.

## Scope

These files help agents answer questions about the `vanducng/skills` catalog and its install paths. They do not replace `AGENTS.md` for repository-local coding instructions or the `SKILL.md` files for skill behavior.
