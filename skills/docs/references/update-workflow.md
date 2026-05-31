# Update Workflow

Use when `./docs/` already has real content and code has drifted from it. If `./docs/` is empty → use `init` instead.

## Pre-flight

1. Confirm `./docs/` exists and has the required files. Missing required files → flag them; create as part of this run.
2. If `--dry-run`: print the plan (Phase 1 + 1.5 + 2 file list with reasons) and stop here.

## Phase 1: Parallel codebase scouting

1. Identify drift sources — what changed since the last doc update?
   - `git log -1 --format=%cI -- docs/` → last doc-touching commit time
   - `git log --since="<that-time>" --oneline` → commits to evaluate
   - If empty or >100 commits → fall back to "last 30 days" or `--since=<ref>` from `$ARGUMENTS`
2. Scope directories that exist — skip `.claude`, `.opencode`, `.git`, `node_modules`, `__pycache__`, `.venv`, `dist`, `build`, `secrets`
3. Probe by doc target — only re-scout surfaces that map to a doc in scope:
   - Lockfile / manifest changes → `tech-stack.md`
   - `.github/workflows/`, `Dockerfile`, `k8s/`, `terraform/` changes → `deployment.md`
   - Lint config or `CONTRIBUTING.md` changes, new dev-setup scripts → `development-guidelines.md`
   - New top-level modules, new public APIs, schema changes → `system-architecture.md`
   - Stack changes, new entry points → `README.md`
4. Activate `vd:scout` (internal mode) on changed surfaces — pass the commit range so it focuses
5. Merge scout reports into a drift digest (≤ 500 lines): what changed, where, which doc it affects

## Phase 1.5: Parallel doc reading

You (main agent) spawn the readers — subagents cannot spawn subagents.

1. `ls docs/*.md README.md 2>/dev/null | wc -l`
2. `wc -l docs/*.md README.md 2>/dev/null | sort -rn`
3. Strategy:
   - 1–3 files → skip parallel; writer reads directly
   - 4–5 files → spawn 2–3 `Explore` agents
   - 6+ files (uncommon for this canonical set) → cap at 4 agents
4. Distribute files by LOC — larger files get a dedicated agent
5. Each agent prompt: "Read these docs. Extract: stated facts that touch code (paths, modules, configs, versions), sections likely stale given this drift digest: <digest summary>. Files: <list>"
6. Merge results into a doc-state digest for the writer

## Phase 2: Documentation update

**Default:** spawn `docs-manager` agent via `Agent` tool with drift digest + doc-state digest.
**`--inline`:** update files from main context using the checklist below.

Pass to writer:
- Drift digest (what changed in code)
- Doc-state digest (what docs claim, what looks stale)
- User's additional requests from `$ARGUMENTS`
- `docs.maxLoc` budget

Files to evaluate (canonical set — only edit if drift digest touches them):

| File | Update when |
|---|---|
| `README.md` | Stack version bump, entry point moved, quick-start broke, new top-level capability worth surfacing |
| `docs/development-guidelines.md` | Lint config changed, conventions evolved, new dev-setup step, new contribution requirement |
| `docs/system-architecture.md` | New component, new integration, data flow changed, module boundary moved, schema migrated |
| `docs/tech-stack.md` | Lockfile bump for a notable lib, new framework/runtime adopted, infra service swapped |
| `docs/deployment.md` | CI workflow added/changed, new environment, new env var, new rollback procedure |

Out-of-scope files — do **not** touch even if drift suggests them: `changelog.md`, `roadmap.md`, `codebase-summary.md`, `prd.md`. If user explicitly names one in `$ARGUMENTS`, surface that they're outside `vd:docs` scope and let them decide.

## Additional requests

<additional_requests>
  $ARGUMENTS
</additional_requests>

## Phase 3: Size check

1. `wc -l docs/*.md README.md 2>/dev/null | sort -rn`
2. Compare to `docs.maxLoc` (default 800)
3. Over budget → split or trim. Ask user before "accept as-is".

## Phase 4: Validation

1. `node $HOME/.claude/scripts/validate-docs.cjs docs/` — code refs, internal links, config keys
2. Report all warnings inline. Non-blocking but informational — a green run after `update` is the goal.

## Hard rules

- **Use `./docs/` as the source of truth** for what's currently claimed — drift digest tells you what to change, doc-state digest tells you what's already there.
- **Do not** write code, fix bugs, or modify anything outside `./docs/` and `./README.md`.
- **Do not** rewrite a file from scratch unless drift touches >50% of it — preserve voice and structure.
- **Do not** invent — every new claim cites a path, SHA, version, or config key.
