# Init Workflow

Use when `./docs/` is missing, empty, or has only a stub README. If `./docs/` already contains real files → use `update` instead.

## Pre-flight

1. Check `./docs/` exists. If not → confirm with user before creating.
2. Check it's empty or near-empty. If populated → suggest `update` and abort.
3. If `--dry-run`: print the plan (Phase 1 + 2 file list) and stop here.

## Phase 1: Parallel codebase scouting

1. List top-level directories that exist — skip `.claude`, `.opencode`, `.git`, `node_modules`, `__pycache__`, `.venv`, `dist`, `build`, `secrets`
2. Activate `vd:scout` (internal mode) to map: stack, entry points, modules, configs, infra, CI workflows, deploy targets
3. Probe specific artifacts to feed each doc:
   - **tech-stack**: `package.json`, `go.mod`, `Cargo.toml`, `pyproject.toml`, `Gemfile`, lockfiles, `*.tool-versions`, `.nvmrc`, `Dockerfile` base images
   - **deployment**: `.github/workflows/`, `.gitlab-ci.yml`, `Dockerfile`, `docker-compose*.yml`, `k8s/`, `terraform/`, `Procfile`, `vercel.json`, `netlify.toml`
   - **development-guidelines**: lint configs (`.eslintrc*`, `ruff.toml`, `.rubocop.yml`, `golangci.yml`), editor config, `CONTRIBUTING.md`, dev setup scripts
   - **system-architecture**: entry points, top-level module structure, public APIs, message buses, DB schemas
4. Merge scout reports into a context digest (≤ 500 lines)

## Phase 2: Documentation creation

**Default:** spawn `docs-manager` agent via `Agent` tool with the scout digest.
**`--inline`:** write the files yourself from main context using the checklist below.

Pass the digest to the writer. Files to create (canonical set):

| File | Content sourced from |
|---|---|
| `README.md` (≤ 300 lines) | Stack summary, quick start (install + run), one-paragraph elevator pitch, links into `./docs/` |
| `docs/development-guidelines.md` | Observed lint configs, naming conventions per language, file-layout rules, local dev setup steps, contribution flow |
| `docs/system-architecture.md` | Components, data flow, integrations, module boundaries — each named with a file path |
| `docs/tech-stack.md` | Language(s) + version, frameworks, runtimes, key libraries (with versions from lockfile), infra/services |
| `docs/deployment.md` | CI/CD workflows (with `.github/workflows/*.yml` references), environments, deploy command, env vars, rollback note |

## Phase 3: Size check

After writes complete:
1. `wc -l docs/*.md README.md 2>/dev/null | sort -rn`
2. Compare to `docs.maxLoc` (session context, default 800)
3. Over budget → split the offending file by section into linked sub-docs. Do not "accept as-is" without user confirmation.

## Phase 4: Validation

1. `node $HOME/.claude/scripts/validate-docs.cjs docs/` — checks code refs, internal links, config keys
2. Report findings inline. Non-blocking, but surface every warning — `init` is when these are cheapest to fix.

## Hard rules

- **Do not** write code, fix bugs, or modify anything outside `./docs/` and `./README.md`.
- **Do not** invent features, modules, or files not in the scout digest.
- **Do not** copy boilerplate from generic templates — every section reflects this codebase.
- **Do not** create `changelog.md`, `roadmap.md`, `prd.md`, or `codebase-summary.md` — those are deliberately out of scope.
