# Internal Scouting - Explore subagents

Default mode. Always available.

## Tool

```
Task(subagent_type: "Explore", prompt: <see template>)
```

Spawn N subagents in **one** message so they run in parallel.

## Prompt template

```
Quickly scout {DIRECTORY_LIST} for files related to: {SEARCH_TARGETS}

Instructions:
- Use Glob and Grep for discovery - do NOT read full files unless explicitly asked
- For each match, report: path, one-line description, why it's relevant to the search target
- Stay strictly inside {DIRECTORY_LIST} - do not wander
- Timeout: 3 minutes max
- Return the report verbatim - no preamble

Report format:
## Found files
- `path/file.ext` - description (why it matches)

## Patterns
- Key conventions you noticed (naming, layout, wiring)

## Gaps
- Anything in scope you couldn't conclude on
```

If your search target is multi-faceted ("auth + session + token validation"), tell each agent which **subset** to focus on. Don't broadcast the same prompt to all agents.

## Spawning strategy

### Logical division (not arbitrary chunks)

Bad - "split the file list in half".
Good - split by **subsystem**: handlers vs services vs schemas vs tests.

See SKILL.md for per-discipline segment templates (software / data / devops / analytics).

### Parallel execution

- One Task tool message containing **all** Explore agent calls
- Each agent gets a distinct, non-overlapping scope
- Total agent count: usually 3–8. Above 8, return diminishes; under 3, do it inline.

## Example - auth scout

User prompt: "Find authentication-related files"

```
Agent 1: Scout src/auth/, src/middleware/    → handlers and middleware
Agent 2: Scout src/api/, src/routes/         → endpoints that gate on auth
Agent 3: Scout tests/                        → auth tests + fixtures
Agent 4: Scout lib/, utils/                  → token / hash / session helpers
Agent 5: Scout config/, env/                 → auth env vars and config
Agent 6: Scout types/, schemas/              → auth contracts and types
```

## Example - data pipeline scout

User: "Find everything wired to the `payments_raw` source"

```
Agent 1: Scout models/staging/, models/intermediate/  → stg_payments*, int_payments*
Agent 2: Scout models/marts/                          → fct_/dim_ models that depend on payments
Agent 3: Scout schema.yml files (recursive)           → source + exposures referencing payments_raw
Agent 4: Scout dags/ or workflows/                    → DAGs that load or trigger payments
Agent 5: Scout lightdash/, dashboards/                → charts/dashboards referencing payments
Agent 6: Scout tests/, macros/                        → custom tests touching payments
```

## Example - infra change scout

User: "Where is the staging env's database URL set?"

```
Agent 1: Scout terraform/, pulumi/      → IaC outputs and secrets-manager refs
Agent 2: Scout k8s/, helm/, kustomize/  → manifests, ConfigMaps, Secrets
Agent 3: Scout env/, environments/      → multi-env overlays (dev/staging/prod)
Agent 4: Scout .github/workflows/       → CI workflows that inject DB URLs
Agent 5: Scout .sops.yaml, secrets/     → encrypted-secret tree
```

## Timeout handling

- 3-minute timeout per agent - `Task` tool already enforces; treat non-response as a timeout
- **Don't restart** timed-out agents - note them as "timed out" in the aggregate
- Aggregate whatever returned; gaps go in the "Gaps" section of the report

## Reading file content (when scouting reveals files you must read)

Stay under ~150K tokens of file content. Chunk large files:

### Step 1 - line count
```bash
wc -l path/to/*.ext
```

### Step 2 - chunk plan
- Target ≤ 500 lines per chunk
- ≤ 3–5 small files per agent, OR 1 large file split across agents

```
chunks = ceil(total_lines / 500)
```

### Step 3 - parallel Bash agents

Small files (<500 lines):
```
Task: subagent_type="Bash", prompt="cat fileA fileB"
```

Large file (>500 lines) - `sed` ranges:
```
Task 1: sed -n '1,500p' big.ext
Task 2: sed -n '501,1000p' big.ext
Task 3: sed -n '1001,1500p' big.ext
```

All in one message → parallel.

### Decision tree

```
< 500 lines        → read whole file
500–1500 lines     → 2–3 chunks
> 1500 lines       → ceil(lines / 500) chunks
```

## Aggregation

1. **Dedup paths** - same file from two agents → one entry, merge descriptions
2. **Merge patterns** - promote conventions seen by 2+ agents to "confirmed"; one-agent-only → "observed"
3. **List timeouts and gaps explicitly** - never paper them over
4. **End with unresolved questions** - what would a second pass need to chase
