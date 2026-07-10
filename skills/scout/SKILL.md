---
name: scout
description: "Fast, parallel codebase scouting across software, data-engineering, devops, and analytics surfaces. Use to locate files, dbt models, dashboards, IaC, pipeline DAGs, K8s manifests, secrets, and CI workflows before changes. Supports internal (Explore subagents) and external (Gemini/OpenCode CLI) modes."
license: MIT
argument-hint: "[search-target] [ext]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Scout

Token-efficient parallel scouting that finds the right files before you touch them. Tuned for multi-discipline repos: app code, data pipelines, IaC, and BI artifacts.

## Modes

| Argument | What | When |
|---|---|---|
| _(none)_ | **Internal** — Explore subagents in parallel (`references/internal-scouting.md`) | Default in Claude Code. Best for ≥6 logical segments. |
| `ext` | **External** — Gemini / OpenCode CLI in parallel (`references/external-scouting.md`) | Large surfaces (1M+ ctx) and you have one of the CLIs installed. SCALE 1–5. |

Internal mode needs the Task/Explore tool (Claude Code). In a runtime without it (e.g. Codex), use `ext` mode — run its `gemini`/`opencode` bash commands sequentially — or fall back to inline `Glob`/`Grep` sweeps.

## When to use

- About to change something that **could span multiple folders** — e.g. add a new dbt source that touches `models/`, `schema.yml`, `dashboards/`, and a CI workflow
- User says **"find / locate / search for"** — code, models, charts, secrets, manifests
- Starting a debug session and need a file map before invoking `vd:debug`
- Before a refactor, migration, or deletion that could ripple across services
- Auditing a repo you don't own well — what's where, and how does it wire together

**Skip scout when** the target file is already known, or one `grep` answers the question. Scout is for breadth, not pinpoint lookups.

## Quick start

1. Parse the prompt → list **search targets** (names, patterns, behaviors)
2. Probe scale with a few `Glob` / `Grep` calls — count matches, list top dirs
3. Decide **SCALE** (number of agents) and divide the repo into **non-overlapping** scopes
4. (If SCALE ≥ 3) register Claude Tasks per agent — see `references/task-management-scouting.md`
5. Spawn agents **in parallel** in a single tool message
6. Aggregate into a **Scout Report** (template below)

## Configuration

External mode reads model from env (no per-user config files):

```bash
GEMINI_MODEL=gemini-3-flash-preview     # default
OPENCODE_MODEL=opencode/grok-code       # default
```

Both are optional. Unset → defaults above.

## Workflow

### 1. Analyze the task

- What exact thing is being searched? Name it (e.g. *"the dbt source for `payments_raw`"*, *"the K8s manifest that mounts the SOPS-encrypted secret"*).
- What dirs are obviously in-scope? What's obviously out-of-scope (vendor, generated, fixtures)?
- Estimate file count via `Glob` / `find . -type f` — this sets SCALE.

### 2. Divide and conquer

Pick **logical segments**, not arbitrary partitions. Examples per discipline below — every agent gets one segment, no overlap.

#### Software repo segments

```
Agent 1: src/<feature>, src/api      → handlers, routes
Agent 2: src/services, src/lib       → business logic, helpers
Agent 3: src/types, src/schemas      → contracts
Agent 4: tests/, e2e/                → test fixtures and specs
Agent 5: config/, scripts/           → wiring and tooling
```

#### Data engineering repo segments

```
Agent 1: models/staging,   models/intermediate     → dbt staging + intermediate
Agent 2: models/marts, snapshots/, seeds/          → dbt marts and seeds
Agent 3: macros/, tests/, analyses/                → reusable SQL + tests
Agent 4: dags/ or workflows/                       → Airflow/Dagster/Prefect DAGs
Agent 5: schema.yml files (recursive)              → sources, exposures, columns
Agent 6: lightdash/, lookml/, looker/, metabase/   → BI semantic layer
```

#### DevOps / infra repo segments

```
Agent 1: terraform/, pulumi/, cdk/                 → IaC modules
Agent 2: k8s/, helm/, kustomize/, manifests/       → cluster manifests
Agent 3: .github/workflows/, .gitlab-ci.yml, Jenkinsfile  → CI/CD
Agent 4: docker/, Dockerfile*, docker-compose*     → container builds
Agent 5: secrets/, .sops.yaml, .age, vault/        → encrypted config
Agent 6: env/, environments/, overlays/            → multi-env overrides (dev/staging/prod)
```

#### Analytics / reporting repo segments

```
Agent 1: dashboards/, .lightdash/                  → dashboard YAML
Agent 2: charts/, viz/, exploratory/               → notebook + chart sources
Agent 3: metrics/, semantic/, dbt models marts     → metric definitions
Agent 4: reports/, exports/                        → scheduled report code
```

Pick whichever segmentation matches the repo. Mixed repos → mix the patterns.

### 3. Register scout tasks (SCALE ≥ 3)

`TaskList()` first — reuse if a scout pipeline already exists this session. Otherwise `TaskCreate` per agent. Schema in `references/task-management-scouting.md`.

Skip task registration if SCALE ≤ 2 (overhead > benefit) or if Task tools are unavailable (use `TodoWrite` instead).

### 4. Spawn parallel agents

- **Internal:** load `references/internal-scouting.md` and spawn N `Explore` subagents in one Task tool message.
- **External:** load `references/external-scouting.md`. Pick `gemini` (SCALE ≤ 3) or `opencode` (SCALE 4–5). Wrap with `timeout 120`.
- Each agent gets: explicit dir scope, search targets, **3-minute timeout**, and the report shape it must return.
- Each agent has <200K tokens — keep prompts terse, hand it the dir list, not the whole repo.

`TaskUpdate` each task to `in_progress` before spawning (skip if Task tools unavailable).

### 5. Collect and aggregate

- Skip non-responders after 3 minutes — log them as "timed out" in the report.
- `TaskUpdate` completed tasks. Mark timeouts in metadata, don't drop them silently.
- Deduplicate paths (different agents may surface the same file). Merge descriptions.
- **Where to save:** write to the injected `Reports:` path. Filename: `scout-{YYYYMMDD-HHMM}-{slug}.md`. Save **only** when the user is going to act on it; for one-shot lookups, print the report inline.

## Report format

```markdown
# Scout Report — {target}

_Date: {YYYY-MM-DD} · Mode: {internal|external} · SCALE: {N}_

## Relevant files
- `path/to/file.ext` — what's in it, why it matters here
- `path/to/another.ext` — …

## Patterns observed
- Convention X is used in {dirs}; convention Y in {dirs}
- Cross-cutting wire: A → B → C

## Surface map (if applicable)
- **Code:** …
- **Data:** dbt models / DAGs / sources implicated
- **Infra:** manifests, IaC modules, env overlays
- **BI:** dashboards / metrics referencing the above

## Gaps / unresolved
- Couldn't determine: …
- Timed out: agent N (scope: …)
- Worth a second pass: …
```

The "Surface map" section is only useful when the change spans disciplines. Drop it for pure-code scouts.

## References

- `references/internal-scouting.md` — Explore subagents (default mode)
- `references/external-scouting.md` — Gemini / OpenCode CLIs (`ext` mode)
- `references/task-management-scouting.md` — Claude Task patterns for coordinating agents
- `references/domain-scouting.md` — search-target playbooks per discipline (data eng, devops, analytics)

## Workflow position

**Typically precedes:** `vd:debug` (investigate after locating), `vd:brainstorm` (design after surveying the surface), `vd:plan` (sequence work), `vd:fix` (fix after locating)

**Compares to:** `Glob`/`Grep` direct — use those for one-target lookups; use scout for **multi-target, multi-dir** surveys

## Quality bar

- **No overlapping scopes** between agents — wasted tokens
- **Names, not vibes** — every report entry includes the file path; "the auth code" is not a finding
- **Dedup on aggregation** — same file from two agents should appear once
- **Honest gaps** — list what wasn't covered, not "comprehensive" when it isn't
