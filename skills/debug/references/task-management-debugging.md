# Debug Task Management

Track investigation pipelines via Claude Tasks (TaskCreate / TaskUpdate / TaskList).

## When to register tasks

| Scope | Tasks? | Rationale |
|---|---|---|
| Single bug, one file | No | Systematic debugging handles directly |
| Multi-component investigation (3+ steps) | Yes | Track assess → collect → analyze → fix → verify |
| Parallel evidence collection | Yes | Coordinate independent log/data gathering |
| Performance investigation across layers | Yes | Track bottleneck per layer |
| CI/CD failure with 3+ hypothesized causes | Yes | Track elimination |
| Pipeline failure spanning source → mart → BI | Yes | Track per-layer evidence |
| Multi-environment infra issue (works in dev, broken in prod) | Yes | Track per-env evidence and diff |

**3-task rule:** skip task creation when investigation has fewer than 3 meaningful steps.

If Task tools are unavailable, use `TodoWrite` with the same fields. Investigation still works; tasks add observability.

## Investigation pipeline as tasks

```
TaskCreate "Assess incident scope"      → pending
TaskCreate "Collect logs & evidence"    → pending, blockedBy: [assess]
TaskCreate "Analyze root cause"         → pending, blockedBy: [collect]
TaskCreate "Implement fix"              → pending, blockedBy: [analyze]
TaskCreate "Verify fix resolves issue"  → pending, blockedBy: [fix]
```

Maps to `investigation-methodology.md` 5-step process. Auto-unblocks as each step completes.

## Task schemas

### Assess

```
TaskCreate(
  subject:     "Assess {incident} scope and impact",
  activeForm:  "Assessing incident scope",
  description: "Symptoms, affected components, recent changes. See investigation-methodology.md Step 1",
  metadata: { debugStage: "assess",
              incident: "{incident}",
              domain: "software|data|devops|analytics|mixed",
              severity: "P0|P1|P2",
              effort: "5m" }
)
```

### Collect

```
TaskCreate(
  subject:     "Collect evidence for {incident}",
  activeForm:  "Collecting evidence",
  description: "Server logs, CI/CD logs, K8s events, dbt run_results, BI compiled SQL. See log-and-ci-analysis.md",
  metadata: { debugStage: "collect",
              incident: "{incident}",
              sources: "logs,ci,k8s,db,dbt,bi",   # whatever applies
              priority: "P1",
              effort: "10m" },
  addBlockedBy: ["{assess-task-id}"]
)
```

### Analyze

```
TaskCreate(
  subject:     "Analyze root cause of {incident}",
  activeForm:  "Analyzing root cause",
  description: "Correlate evidence, trace execution / lineage, identify root cause. See systematic-debugging.md Phase 1-3 + domain-specific reference",
  metadata: { debugStage: "analyze",
              incident: "{incident}",
              technique: "systematic|root-cause-tracing|pipeline|infra|analytics",
              priority: "P1",
              effort: "15m" },
  addBlockedBy: ["{collect-task-id}"]
)
```

### Fix

```
TaskCreate(
  subject:     "Fix root cause: {root_cause_summary}",
  activeForm:  "Implementing fix",
  description: "Address root cause, add defense-in-depth. See defense-in-depth.md + domain-specific reference",
  metadata: { debugStage: "fix",
              rootCause: "{root_cause}",
              priority: "P1",
              effort: "20m" },
  addBlockedBy: ["{analyze-task-id}"]
)
```

### Verify

```
TaskCreate(
  subject:     "Verify fix with fresh evidence",
  activeForm:  "Verifying fix",
  description: "Run tests, check build, confirm issue resolved with fresh output. NO CLAIMS WITHOUT EVIDENCE. See verification.md",
  metadata: { debugStage: "verify",
              priority: "P1",
              effort: "5m" },
  addBlockedBy: ["{fix-task-id}"]
)
```

## Parallel evidence collection

For multi-source investigations, spawn collection agents in parallel:

```
# Parallel - no blockedBy among them
TaskCreate(subject: "Collect CI/CD pipeline logs",
  metadata: { debugStage: "collect", source: "ci",
              agentIndex: 1, totalAgents: 4, priority: "P1" })

TaskCreate(subject: "Collect application server logs",
  metadata: { debugStage: "collect", source: "server",
              agentIndex: 2, totalAgents: 4, priority: "P1" })

TaskCreate(subject: "Query database for anomalies",
  metadata: { debugStage: "collect", source: "db",
              agentIndex: 3, totalAgents: 4, priority: "P1" })

TaskCreate(subject: "Pull K8s events and pod logs",
  metadata: { debugStage: "collect", source: "k8s",
              agentIndex: 4, totalAgents: 4, priority: "P1" })

# Analyze blocks on ALL collection tasks
TaskCreate(subject: "Analyze root cause from collected evidence",
  addBlockedBy: ["{ci}", "{server}", "{db}", "{k8s}"])
```

## Pipeline-failure pattern (data eng)

```
TaskCreate "Assess: which DAG / model / source"
TaskCreate "Collect: target/run_results.json + task logs"
TaskCreate "Analyze: source / schema-drift / logic / orchestration / idempotency / resource"
TaskCreate "Fix: at the identified layer"
TaskCreate "Backfill the affected window (if any)"
TaskCreate "Verify: row counts, dbt tests, downstream marts"
```

## Multi-env-divergence pattern (devops)

```
TaskCreate "Assess: which env(s) broken"
TaskCreate "Collect dev manifest + env vars" (parallel)
TaskCreate "Collect staging manifest + env vars" (parallel)
TaskCreate "Collect prod manifest + env vars" (parallel)
TaskCreate "Diff: where the working and broken envs differ"
TaskCreate "Fix: in the source of the difference (Helm values / overlay / IaC)"
TaskCreate "Verify: deploy + reach the actual env, see fresh logs"
```

## Wrong-number pattern (analytics)

```
TaskCreate "Assess: which metric / chart, what the right number is"
TaskCreate "Collect: dashboard SQL, semantic-layer SQL, mart SQL"
TaskCreate "Analyze: first divergence point" (cross-layer comparison)
TaskCreate "Fix: at the divergence layer (definition / mart / filter)"
TaskCreate "Verify: rerun + cross-check another consumer of the same metric"
```

## Lifecycle

```
Assess   → in_progress → completed (scope + impact)
Collect  → in_progress → completed (evidence)
Analyze  → in_progress → completed (root cause)
Fix      → in_progress → completed (fix in place)
Verify   → in_progress → completed (fresh evidence)
```

### Re-investigation cycle

When fix doesn't resolve the issue → new analyze → fix → verify cycle:

```
TaskCreate(subject: "Re-analyze: fix attempt {N} failed",
  addBlockedBy: ["{verify-task-id}"],
  metadata: { debugStage: "analyze", cycle: 2, priority: "P1" })
```

Limit to 3 cycles. After cycle 3 → question architecture (`systematic-debugging.md` Phase 4.5).

## Integration with cook / planning

Debug tasks are **separate** from cook/planning phase tasks.

When cook spawns the debugger:
1. Cook hits failing tests → spawns debug pipeline
2. Debug pipeline executes (assess → collect → analyze → fix → verify)
3. All debug tasks complete → cook marks the phase debugging as done
4. Cook proceeds to next phase

## Report sync-back

After investigation completes, write a diagnostic report per `reporting-standards.md`. The report persists across sessions; tasks are session-scoped.

## Error handling

If `TaskCreate` fails - log a warning, continue with sequential debugging. Tasks add visibility, not core function.
