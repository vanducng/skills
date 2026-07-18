# Repository Guidelines

## Project Structure & Module Organization

This repository is a daily-driver collection of skills for agentic coding, described by `skills.toml`. Skill packages live under `skills/<name>/` and each package must include `SKILL.md` with valid frontmatter. Skill-specific scripts, references, and assets stay inside that skill directory, for example `skills/file-browser/scripts/` and `skills/file-browser/assets/`. Repository helpers live in `scripts/` (install/uninstall/validate/check-*). The `vd` CLI that installs and manages these skills lives in a separate repo, not here. Agent-generated working artifacts (reports, plans, visuals, journals, state) live under a gitignored `.workbench/` umbrella when the project opts in via `.vd.json` (`paths.umbrella`); otherwise the legacy `plans/` layout applies. With `paths.layout: feature-first` set, those artifacts nest per-feature under `.workbench/features/{ticket}-{slug}/{plans,reports,visuals,journals,state}/` (plus root-level `_global/` and `_archive/`), managed by the `workbench` skill, instead of flat type-first siblings. Producer skills always write to the hook-injected `Reports:`/`Plans:`/`Visuals:`/`Journals:` paths — never construct the layout by hand (enforced by `scripts/check-skill-paths.sh`).

## Build, Test, and Development Commands

- `bash scripts/new-skill.sh my-new-skill`: scaffold a new skill directory.
- `bash scripts/validate.sh`: validate every `skills/*/SKILL.md` frontmatter block.
- `bash scripts/install.sh` / `scripts/uninstall.sh`: install/remove the skills locally (Claude Code dev symlinks into `~/.claude/skills` only; use `vd install codex` for the Codex `~/.agents/skills` namespace).
- `bash scripts/check-docs-site.sh --check`: verify `docs/` tracks the catalog.
- `bash scripts/check-install-conflicts.sh`: check for skill ID/file conflicts.
- `cd skills/file-browser && npm test`: run the file-browser server tests.
- `cd skills/file-browser && npm start`: run the local file-browser server.

## Coding Style & Naming Conventions

Use kebab-case for skill directory names and match the `name` field in `SKILL.md` exactly, such as `browser-trace`. Keep skill instructions direct, scoped, and supported by local `references/`, `scripts/`, or `assets/` when useful. Shell scripts should use `set -euo pipefail`.

When documenting skill handoffs or examples, use canonical skill IDs without a leading invocation prefix, such as `vd:cook plans/path/`. The caller adds the slash prefix in Claude Code or the dollar prefix in Codex.

Skills must work across computers and users. Never hardcode personal absolute paths, usernames, or machine-only locations; use repository-relative paths, `$HOME`, configurable environment variables, or hook-injected artifact roots. If a platform-specific default is necessary, document a portable override.

## Documentation Sync

The `skills/` directory is the source of truth for the catalog; `docs/` must track it. When you add, remove, or rename a skill — or materially change what one does — update the docs in the same change:

- `docs/content/skills.md`: place the skill in the taxonomy tables and keep the catalog count accurate.
- `docs/content/index.mdx`: update the skill-count metric when it changes.
- `llms.txt` / `llms-full.txt` are generated at docs build time by the starlight-llms-txt plugin — no manual edits.

Validate before committing with `bash scripts/check-docs-site.sh --check`. A skill change that ships without the matching docs update is incomplete.

## Testing Guidelines

Run `bash scripts/validate.sh` for any skill change, and `bash scripts/check-docs-site.sh --check` when the catalog changes. Skills that ship their own tests (e.g. `skills/file-browser`) run them via the skill's own tooling (`npm test`).

## Commit & Pull Request Guidelines

Commit history follows Conventional Commits. Use scopes for focused components, for example `feat(file-browser): add preview mode` or `fix(diagram): validate skeleton schema`. Skill-only changes may omit a scope, as in `feat: add my-new-skill`. Do not mention AI tools in commit messages. Pull requests should describe the change, list validation commands run, link related issues, and include screenshots or sample output when changing rendered assets, browser UI, diagrams, or CLI output.
