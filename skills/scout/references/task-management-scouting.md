# Scout Task Management

Track parallel scout agents via Claude Tasks (TaskCreate / TaskUpdate / TaskList).

## When to register tasks

| Agents | Tasks? | Why |
|---|---|---|
| ≤ 2 | No | Overhead > benefit |
| ≥ 3 | Yes | Coordination + progress visibility justify the cost |

If Task tools are unavailable (some IDE harnesses), use `TodoWrite` with the same fields. The scouting workflow keeps working - tasks add observability, not functionality.

## Registration flow

```
TaskList()                 → already-registered scout tasks for this session?
  found  → reuse
  empty  → TaskCreate per agent
```

## Task schema

```
TaskCreate(
  subject:     "Scout {scope} for {target}",
  activeForm:  "Scouting {scope}",
  description: "Search {dir-list} for {patterns}; report paths + one-liners",
  metadata: {
    agentType:    "Explore",        # "Explore" (internal) | "Bash" (external)
    scope:        "src/auth/,src/middleware/",
    domain:       "software",       # software | data | devops | analytics | mixed
    scale:        6,
    agentIndex:   1,                # 1-indexed
    totalAgents:  6,
    toolMode:     "internal",       # internal | external
    externalTool: "gemini",         # only when toolMode=external
    priority:     "P2",             # scout = coordination, not primary work
    effort:       "3m"
  }
)
```

### Required

- `agentType`, `scope`, `scale`, `agentIndex`, `totalAgents`, `toolMode`, `priority`, `effort`

### Optional

- `domain` - useful filter when multi-discipline scouts run in the same session
- `searchPatterns` - key patterns this agent grepped for (aids debug if results disappoint)
- `externalTool` - when `toolMode=external`

## Lifecycle

```
register   → status=pending
spawn      → TaskUpdate status=in_progress
return     → TaskUpdate status=completed
timeout    → keep status=in_progress, add metadata.error="timeout"
```

Keeping timeouts as `in_progress` (not `completed`) lets `TaskList` distinguish "agent never returned" from "agent finished".

## Examples

### Software, internal, SCALE=6

```
TaskCreate(
  subject:     "Scout src/auth/ for auth files",
  activeForm:  "Scouting src/auth/",
  metadata: { agentType:"Explore", scope:"src/auth/", domain:"software",
              scale:6, agentIndex:1, totalAgents:6, toolMode:"internal",
              priority:"P2", effort:"3m" }
)
# → repeat for agents 2–6 with distinct scopes
```

### Data eng, internal, SCALE=4

```
TaskCreate(
  subject:     "Scout dbt models for payments lineage",
  activeForm:  "Scouting models/",
  metadata: { agentType:"Explore", scope:"models/staging/,models/intermediate/,models/marts/",
              domain:"data", scale:4, agentIndex:1, totalAgents:4,
              toolMode:"internal", priority:"P2", effort:"3m" }
)
```

### DevOps, external (gemini), SCALE=3

```
TaskCreate(
  subject:     "Scout infra repo for DATABASE_URL surface",
  activeForm:  "Scouting infra via gemini",
  metadata: { agentType:"Bash", scope:"terraform/,k8s/,helm/,.sops.yaml",
              domain:"devops", scale:3, agentIndex:1, totalAgents:3,
              toolMode:"external", externalTool:"gemini",
              priority:"P2", effort:"3m" }
)
```

## Integration with cook / planning tasks

Scout tasks are **independent** from phase tasks - not parent/child.

**Why:** different lifecycle. Scout finishes before cook continues. Mixing them confuses `TaskList`.

**When cook spawns scout:**
1. Cook step → planner → planner spawns scout
2. Scout registers its **own** tasks, executes, aggregates
3. Scout returns report → planner continues
4. Cook hydrates phase tasks (separate entities)

## Quality check

After registration, print one line:

```
✓ Registered N scout tasks ({mode} mode, SCALE={N}, domain={domain})
```

## Error handling

If `TaskCreate` fails - log a warning, proceed without task tracking. Scout still works; we just lose observability.
