# Repository Guidelines

## Project Structure & Module Organization

This repository contains skills for agentic coding plus the `vd` CLI used to manage them. Skill packages live under `skills/<name>/` and each package must include `SKILL.md` with valid frontmatter. Skill-specific scripts, references, and assets stay inside that skill directory, for example `skills/file-browser/scripts/` and `skills/file-browser/assets/`. Repository helpers live in `scripts/`. The Go CLI is a separate module in `tools/vd/`, with source under `tools/vd/internal/`, command entrypoint under `tools/vd/cmd/vd`, docs under `tools/vd/docs/`, and tests beside the packages they cover.

## Build, Test, and Development Commands

- `bash scripts/new-skill.sh my-new-skill`: scaffold a new skill directory.
- `bash scripts/validate.sh`: validate every `skills/*/SKILL.md` frontmatter block.
- `cd tools/vd && make build`: compile the CLI to `tools/vd/vd`.
- `cd tools/vd && make test`: run `go test ./...` for the CLI module.
- `cd tools/vd && make lint`: run `golangci-lint run` when available.
- `cd skills/file-browser && npm test`: run the file-browser server tests.
- `cd skills/file-browser && npm start`: run the local file-browser server.

## Coding Style & Naming Conventions

Use kebab-case for skill directory names and match the `name` field in `SKILL.md` exactly, such as `browser-trace`. Keep skill instructions direct, scoped, and supported by local `references/`, `scripts/`, or `assets/` when useful. Shell scripts should use `set -euo pipefail`. Go code in `tools/vd/` should be `gofmt`/`goimports` formatted, package-oriented, and kept within the CLI module unless a cross-repo change is intentional.

When documenting skill handoffs or examples, use canonical skill IDs without a leading invocation prefix, such as `vd:cook plans/path/`. The caller adds the slash prefix in Claude Code or the dollar prefix in Codex.

## Testing Guidelines

Run `bash scripts/validate.sh` for any skill change. For CLI changes, run `cd tools/vd && make test`; use `go test ./... -race -cover` before risky changes. Snapshot behavior for bundle output is covered in `tools/vd/internal/target/claude_bundle_test.go`; update golden files only when the emitted plugin output intentionally changes. Name Go tests with standard `TestXxx` functions in `*_test.go` files colocated with the package.

## Commit & Pull Request Guidelines

Commit history follows Conventional Commits. Use scopes for focused components, for example `feat(file-browser): add preview mode`, `fix(diagram): validate skeleton schema`, or `feat(vd): add --dry-run`. Skill-only changes may omit a scope, as in `feat: add my-new-skill`. Do not mention AI tools in commit messages. Pull requests should describe the change, list validation commands run, link related issues, and include screenshots or sample output when changing rendered assets, browser UI, diagrams, or CLI output.
