# Repository Guidelines

## Project Structure & Module Organization

This repository is a daily-driver collection of skills for agentic coding, described by `skills.toml`. Skill packages live under `skills/<name>/` and each package must include `SKILL.md` with valid frontmatter. Skill-specific scripts, references, and assets stay inside that skill directory, for example `skills/file-browser/scripts/` and `skills/file-browser/assets/`. Repository helpers live in `scripts/` (install/uninstall/validate/check-*). The `vd` CLI that installs and manages these skills lives in a separate repo, not here. Agent-generated working artifacts (reports, plans, visuals, journals, state) live under a gitignored `.workbench/` umbrella when the project opts in via `.vd.json` (`paths.umbrella`); otherwise the legacy `plans/` layout applies. With `paths.layout: feature-first` set, those artifacts nest per-feature under `.workbench/features/{ticket}-{slug}/{plans,reports,visuals,journals,state}/` (plus root-level `_global/` and `_archive/`), managed by the `workbench` skill, instead of flat type-first siblings. Producer skills always write to the hook-injected `Reports:`/`Plans:`/`Visuals:`/`Journals:` paths - never construct the layout by hand (enforced by `scripts/check-skill-paths.sh`).

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

The `skills/` directory is the source of truth for the catalog; `docs/` must track it. When you add, remove, or rename a skill - or materially change what one does - update the docs in the same change:

- `docs/content/skills.md`: place the skill in the taxonomy tables and keep the catalog count accurate.
- `docs/content/index.mdx`: update the skill-count metric when it changes.
- `llms.txt` / `llms-full.txt` are generated at docs build time by the starlight-llms-txt plugin - no manual edits.

Validate before committing with `bash scripts/check-docs-site.sh --check`. A skill change that ships without the matching docs update is incomplete.

## Testing Guidelines

Run `bash scripts/validate.sh` for any skill change, and `bash scripts/check-docs-site.sh --check` when the catalog changes. Skills that ship their own tests (e.g. `skills/file-browser`) run them via the skill's own tooling (`npm test`).

## Commit & Pull Request Guidelines

Commit history follows Conventional Commits. Use scopes for focused components, for example `feat(file-browser): add preview mode` or `fix(diagram): validate skeleton schema`. Skill-only changes may omit a scope, as in `feat: add my-new-skill`. Do not mention AI tools in commit messages. Pull requests should describe the change, list validation commands run, link related issues, and include screenshots or sample output when changing rendered assets, browser UI, diagrams, or CLI output.

## Cursor Cloud specific instructions

The base image already provides everything the core suite needs: Bash, Python 3 (stdlib only), Node.js 22, and Go. The cloud update script only runs `npm install` in the two sub-projects that have lockfiles (`skills/file-browser` and `docs`); everything else needs no dependency install.

- Core validation + tests (the same suite as `.github/workflows/validate.yml`) run with zero dependency install: `bash scripts/validate.sh`, the `python3` hook/skill test files listed in that workflow, `bash scripts/check-release-versions.sh`, and `bash scripts/check-docs-site.sh --check`. See the "Build, Test, and Development Commands" and "Testing Guidelines" sections above for the canonical commands.
- `skills/file-browser`: after `npm install` (its `postinstall` fetches PDF.js viewer assets), run `npm test` / `npm start`. Non-obvious runtime caveats when launching the server directly (`node scripts/server.cjs`): it takes CLI flags (`--dir <path>` or `--file <path>`), NOT env vars; it forks/backgrounds by default, so pass `--foreground` to keep it in the current process; and it only binds within ports 3556–3600 (`--port` outside that range fails with "No available port"). It binds to `localhost` by default. Browse a directory at `/browse?dir=<url-encoded-abs-path>` and view a file at `/view?file=<url-encoded-abs-path>`.
- `docs`: after `npm install`, build with `npm run build` or serve with `npm run dev` (Astro + Starlight). `llms*.txt` are generated at build time — never hand-edit.
- Other skills carry optional, skill-specific dependencies (e.g. `skills/twitter` and `skills/omnimedia` Python `requirements.txt`, `skills/show-off/scripts` and `skills/browser-trace` npm packages, plus various external API keys/CLIs). These are intentionally NOT installed by the update script; install them on demand only when exercising that specific skill.
