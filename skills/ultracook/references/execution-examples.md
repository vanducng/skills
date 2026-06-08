# Execution examples

Worked examples of mode choice in Claude Code. Use when mode choice is unclear.

## Small typo

```text
Use $ultracook to fix this typo in README.
```

**Mode: direct.** Workflow overhead would exceed the work.

- Edit the typo, inspect the diff, note a full workflow wasn't needed.

## Broad audit, no delegation wording

```text
Audit this repo for slow startup paths and give me a fix plan.
```

**Mode: workflow** (broad investigation, but no explicit ultracook/agent ask).

- Create a run dir per the run-root rule.
- Write `plan.md`, `orchestration.md`, `state.json`.
- Packets: `01-entry-points`, `02-startup-costs`, `03-fix-plan` — execute as isolated parent passes, notes in `results/`.
- Integrate before the final answer.

## Feature with explicit ultracook + "split across agents"

```text
Use $ultracook. Split this across agents and implement the settings export feature.
```

**Mode: delegated.** Strong delegation wording + Claude Code exposes native primitives.

- Run `vd:plan` first to produce `plans/<slug>/` with phases.
- Write `orchestration.md` before delegating.
- Keep the blocking architecture path in the parent session.
- Dispatch independent packets:
  - `Explore` subagent / `vd:scout`: find settings storage + existing export patterns (read-only).
  - `Task` write-capable: implement backend export route in named files (disjoint scope).
  - `Task` write-capable: add UI button + loading state in named files (disjoint scope).
  - `Explore` subagent: find tests and fixtures.
- Each write packet has a disjoint write scope. Own integration, then `vd:cook` (verify) + `vd:code-review`.

## Repo-wide migration (Workflow tool)

```text
Use $ultracook to migrate all API clients to the new SDK.
```

**Mode: delegated via the `Workflow` tool** — many independent sites, pipeline-shaped, exceeds one context.

- Approval gate: broad codemod + dependency change + possible behavior change. Ask before broad rewrites.
- Scout the call sites inline first to build the work-list.
- Author a `Workflow` script: `pipeline(sites, transform, verify)` with `isolation: 'worktree'` if agents mutate files in parallel.
- Continue with read-only mapping only if approval isn't granted.

## Ultracook only, size unknown

```text
Ultracook: implement the settings export feature end to end.
```

**Mode: direct, workflow, or delegated** depending on size, independent-packet value, and risk. `ultracook` authorizes choosing the depth.

- Create artifacts if non-trivial. Split discovery/implementation/verification into packets when useful.
- Use `Task`/`Workflow` delegation when packets are genuinely independent; otherwise stay inline.

## No native delegation available

```text
Use $ultracook and run parallel agents for this audit.
```

**Mode: workflow fallback** when the host can't spawn agents.

- Say native delegation is unavailable in this environment.
- Create packet files, execute isolated parent passes, keep evidence separate per result file.
