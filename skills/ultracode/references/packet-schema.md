# Packet schema

Use this reference when creating or validating workflow artifacts.

## Run layout

```text
<run-root>/
  plan.md
  orchestration.md
  state.json
  packets/
    01-discovery.md
  results/
    01-discovery.md
  integration.md
  final-report.md
```

`<run-root>` is the active `vd:plan` plan directory when one exists, otherwise `plans/ultracode/<slug>/`. Reports/final summaries go under `plans/reports/`.

## plan.md

Required sections (or generate via `vd:plan`):

```text
# <task title>

## Goal
## Success criteria
## Current context
## Constraints
## Risk level
## Approval gates
## Mode
## Work packets
## Integration policy
## Verification plan
## Completion criteria
```

## orchestration.md

Required sections — keep short; this is the execution contract, not a transcript:

```text
# Orchestration

## Parent critical path
## Packets
## Delegation
## Agents
## Wait points
## Fallback
## Verification order
```

## state.json

Required keys:

```json
{
  "title": "string",
  "slug": "string",
  "created_at": "ISO-8601 string",
  "updated_at": "ISO-8601 string",
  "status": "planning",
  "mode": "direct|workflow|delegated",
  "approval": {
    "required": false,
    "granted": null,
    "notes": ""
  },
  "delegation": {
    "primitive": "none|workflow-tool|task-subagent|codex-spawn|other",
    "native_agent_available": false,
    "native_agent_used": false,
    "notes": ""
  },
  "packets": [
    {
      "id": "01-discovery",
      "status": "pending",
      "owner": "parent|read-only-agent|write-capable-agent",
      "route": "inline|vd:scout|vd:cook|vd:debug|Task|Workflow",
      "write_scope": [],
      "result_path": "results/01-discovery.md"
    }
  ],
  "verification": {
    "status": "pending",
    "checks": [
      {
        "name": "unit tests",
        "command": "make test",
        "required": true,
        "status": "pending",
        "evidence": ""
      }
    ]
  }
}
```

Allowed run `status`: `planning`, `waiting_for_approval`, `executing`, `integrating`, `verifying`, `complete`, `blocked`, `cancelled`.

Allowed packet `status`: `pending`, `in_progress`, `complete`, `blocked`, `skipped`.

Note: Claude Code workflow scripts can't call `Date.now()`/`new Date()` — stamp `created_at`/`updated_at` from the parent session, not from inside a `Workflow` script.

## Packet files

```text
# Packet <id>: <name>

## Objective
## Context
## Sources
## Ownership
## Route
## Do
## Do not
## Expected output
## Verification
## Handoff format
```

For code-edit packets, also include:

```text
## Write scope

- path/to/file-a
- path/to/module/

## Coordination rule

You are not alone in the codebase. Do not revert edits made by others. Adapt to nearby changes.
```

## Result files

```text
# Result <id>: <name>

## Summary
## Evidence
## Files changed
## Decisions
## Risks
## Verification run
## Open questions
```

## integration.md

```text
# Integration

## Accepted
## Rejected
## Conflicts
## Decisions
## Final changes
## Verification still needed
## Remaining risks
```

## final-report.md

```text
# Final report

## Outcome
## What changed
## Verification
## Skipped checks
## Remaining risks
## Next useful step
```

## Naming rules

- Two-digit packet prefixes: `01-discovery`, `02-tests`.
- Lowercase hyphen-case slugs, under 64 characters.
- Match result names to packet IDs.
- Don't mark work complete without evidence in `verification.checks` or `final-report.md`.
