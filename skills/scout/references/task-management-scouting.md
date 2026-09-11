# Scout Task Management

Track parallel scout agents via Claude Tasks (TaskCreate / TaskUpdate / TaskList). Register when SCALE ≥ 3 (coordination justifies the cost); skip at SCALE ≤ 2. If Task tools are unavailable (some IDE harnesses), use `TodoWrite` with the same fields - tasks add observability, not functionality.

## Registration flow

`TaskList()` first - reuse an existing scout pipeline for the session; otherwise `TaskCreate` per agent. `TaskUpdate` each task to `in_progress` before spawning.

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

Optional: `searchPatterns` (key patterns this agent grepped for - aids debug if results disappoint). `domain` is the useful filter when multi-discipline scouts run in one session.

## Lifecycle

```
register   → status=pending
spawn      → TaskUpdate status=in_progress
return     → TaskUpdate status=completed
timeout    → keep status=in_progress, add metadata.error="timeout"
```

Keeping timeouts as `in_progress` (not `completed`) lets `TaskList` distinguish "agent never returned" from "agent finished".

## Integration with cook / planning tasks

Scout tasks are **independent** from phase tasks - not parent/child. Scout finishes before cook continues; mixing the two confuses `TaskList`. Cook hydrates its phase tasks as separate entities after the scout report returns.

## Failure handling

If `TaskCreate` fails - log a warning, proceed without task tracking. Scout still works; you just lose observability. After registration, print: `✓ Registered N scout tasks ({mode} mode, SCALE={N}, domain={domain})`.
