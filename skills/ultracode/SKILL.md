---
name: ultracode
description: "Run a disciplined multi-agent workflow for serious coding tasks: classify, plan, packetize, delegate when it helps, integrate, and verify. Use when the user types ultracode, $ultracode, ultra code, or asks for a dynamic/multi-agent/subagent/parallel workflow, agent swarm, 'delegate this', 'split this across agents', or an independent verification pass. In Claude Code, maps directly onto the native Workflow tool and Task/Agent subagents and routes packet work through the vd: skill stack."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# Ultracode

A disciplined operating procedure for work that needs planning, packetization, agent delegation, integration, and verification. Use the smallest workflow that can prove the result — no ceremony for small tasks.

This is a skill, not a runtime: no bundled runner, no hidden scripts. It tells the current agent *how* to orchestrate using whatever primitives the host exposes. The host's own system rules and tools always win.

## Contract

- This is a user-authored skill, not an official Anthropic/OpenAI/Google feature. Don't claim otherwise.
- No bundled runtime or required scripts — orchestrate with native host tools and plain Markdown/JSON artifacts.
- Treat an explicit `ultracode`, `$ultracode`, or "ultra code" request as permission to choose **delegated mode** when the host allows it.
- Don't commit, push, publish, or deploy unless the user explicitly asks (then `vd:ship` / `vd:git`).
- In Claude Code, prefer the native **Workflow** tool for real fan-out/pipeline work and **Task/Agent** subagents for ad-hoc parallel packets. In other hosts, use the closest native primitive; if none exists, fall back to workflow-mode artifacts and say so.

## First pass — classify

Before acting, classify the task:

- **type**: research, code change, bug fix, migration, audit, docs, design, QA, release
- **risk**: low, medium, high
- **blast radius**: single file, module, repo-wide, external system
- **verification**: none, command, tests, build, browser, manual checklist
- **delegation**: useful, not useful, allowed by host, blocked by environment

Then choose one mode.

## Modes

### Direct mode

Small, clear tasks that don't benefit from packets: answer a narrow question, inspect one file, run one command, fix a typo, change one small function.

- Do the task directly. No artifacts unless asked.
- Verify with the narrowest useful check.
- Mention the full workflow wasn't needed only when useful.

### Workflow mode

Multiple phases, meaningful uncertainty, or enough risk to separate work packets — but native delegation is unavailable or not warranted: broad audit, research + plan, multi-step refactor, feature with discovery/implementation/verification.

- Create a run directory (see [Run root](#workflow-artifacts)).
- Write `plan.md`, `orchestration.md`, `state.json`, packet files, result notes, `integration.md`, `final-report.md`.
- Execute packets as isolated passes in the parent session.
- Integrate all results before final verification.

### Delegated mode

The host exposes native delegation, the task has independent packets, and delegation is permitted. An explicit `ultracode` invocation is delegation permission when the host lets the skill choose depth.

- Create orchestration artifacts **before** delegating.
- Keep the immediate blocking task in the parent session.
- Delegate bounded, non-blocking sidecar work — prefer it for read-heavy exploration, tests, triage, summarization.
- Use write-capable agents only when file ownership is disjoint and explicit.
- Tell write agents: *you are not alone in the codebase; do not revert others' edits; adapt to nearby changes.*
- Wait only when a delegated result blocks the next parent step. Integrate before final verification.

If native delegation is unavailable, fall back to workflow mode and say so briefly.

## Host delegation primitives

| Host | Preferred primitive | Notes |
| --- | --- | --- |
| **Claude Code** | `Workflow` tool for deterministic fan-out/pipeline; `Task`/`Agent` subagents for ad-hoc parallel packets | The `ultracode` keyword opts the session into the Workflow tool. See [Claude Code mapping](#claude-code-mapping). |
| Codex | `spawn_agent` → `wait_agent`/`send_input`/`close_agent` | `explorer` for read-only packets, `worker` for bounded write packets. Self-contained prompts; don't pair an agent type with a full-history fork. |
| Other hosts | Closest native agent/task primitive | Never invent a runner. Fall back to workflow-mode artifacts when none exists. |

## Claude Code mapping

In Claude Code, don't reinvent orchestration — drive the native primitives and route packets through the `vd:` stack.

**Pick the delegation primitive:**

- **`Workflow` tool** — when packets form a fan-out or multi-stage pipeline, need adversarial/independent verification, or exceed one context (repo-wide audit, migration over many sites, N-finder review). Use `pipeline()` by default; reserve `parallel()` barriers for genuine cross-item joins. This is the heavy primitive the `ultracode` keyword unlocks.
- **`Task`/`Agent` subagents** — for a handful of independent packets you launch and integrate yourself (parallel exploration, one-off write packets with disjoint ownership). Send independent agents in a single message so they run concurrently. Use specialized subagent types (`Explore`, `code-reviewer`, `tester`, `researcher`) when they fit.

**Route packets to existing skills instead of hand-rolling the phase:**

| Packet intent | Route to |
| --- | --- |
| Locate files / map the surface | `vd:scout` (or `Explore` subagents) |
| Deep technical research / option eval | `vd:research`, `vd:brainstorm` |
| Turn an approach into a phased plan | `vd:plan` (writes `plans/<slug>/`) |
| Execute a plan phase-by-phase | `vd:cook` |
| Diagnose a failure to root cause | `vd:debug`, `vd:fix` |
| Run tests / coverage | `vd:test` |
| Review the diff before landing | `vd:code-review`, `vd:security` |
| Land the branch (only when asked) | `vd:ship`, `vd:git` |
| Autonomous metric/goal loop | `vd:auto-loop`, `vd:optimize-loop` |

Ultracode is the orchestration layer **above** these: it classifies the task, picks the mode, packetizes, dispatches to the right skill or subagent, then owns integration and verification. For a full feature this often means: `vd:plan` → ultracode fans implementation packets across `Task`/`Workflow` → `vd:test` → `vd:code-review`. Stay in the loop between phases; read each result before the next dispatch.

## Workflow artifacts

**Run root rule:**

- If an active plan directory exists (from `vd:plan`, e.g. `plans/<date>-<slug>/`), reuse it — add `orchestration.md`, `state.json`, `packets/`, `results/` alongside the existing `plan.md` and phase files.
- Otherwise default to `plans/ultracode/<slug>/`.
- If project instructions name a different scratch/plans directory, use that.
- Final summaries and reports go under `plans/reports/` per repo convention.

Run layout:

```text
<run-root>/
  plan.md
  orchestration.md
  state.json
  packets/
  results/
  integration.md
  final-report.md
```

Read `references/packet-schema.md` when filling packet files, result files, `orchestration.md`, or `state.json`.

## Plan

Keep `plan.md` concrete: goal, success criteria, current context, constraints, risk level, approval gates, mode, work packets, integration policy, verification plan, completion criteria. Don't let the plan replace execution. (For non-trivial features, generate this via `vd:plan` instead of hand-writing it.)

## Orchestration

Keep `orchestration.md` short and operational — it's the execution contract, not a transcript: parent critical path, packet list with owners, agents/subagents to spawn, wait points, fallback if delegation is unavailable, verification order.

## Delegation policy

Before spawning or invoking another agent:

- Identify the parent critical path and keep it local.
- Confirm the packet is bounded and non-blocking.
- Assign explicit ownership; state read-only vs write-capable.
- Don't duplicate packet work across agents.

Never use delegation to avoid understanding the integration path.

## Approval gates

Ask one clear yes/no question before: deletion, overwrite, mass rename, force push; publishing, deploying, emailing, posting; production data; credentials/secrets/billing/accounts; broad codemods; expensive/long-running agent swarms; irreversible repo operations.

If approval is missing, continue only with safe read-only work, local drafts, or non-destructive checks. Read `references/approval-gates.md` when risk is ambiguous.

## Packet design

Good packets are narrow, bounded, evidence-based.

- **Good read-only**: find entry points for a feature; trace data flow route→storage; find existing tests/fixtures; identify migration risk; compare behavior with docs.
- **Good write-capable**: update validation in named files; add tests for one module; update docs only; refactor one isolated adapter.
- **Bad**: "fix the whole thing", "figure it out", "implement everything", "edit any files you need".

For code-edit packets, assign non-overlapping files or modules.

### Agent prompt shapes

Read-only:

```text
You are working in the same repo as other agents.
Task: <specific read-only objective>
Do: inspect only the listed sources unless one nearby hop is required; cite file:line; return concise findings with evidence.
Do not: edit files; run destructive commands; duplicate other packet work.
Output: summary, evidence, risks, recommended parent action.
```

Write-capable:

```text
You are not alone in the codebase. Other agents may edit other files.
Do not revert edits made by others. Adapt to nearby changes.
Ownership: <files or module>
Task: <specific implementation task>
Do: edit only owned files unless blocked; add/update focused tests if the area has them; list changed files.
Do not: change public behavior outside this packet; run broad formatting; rewrite unrelated code; commit/push/publish/deploy.
Output: files changed, summary, verification run, risks or blockers.
```

## Integration

The parent session owns integration. After packet work: read each result; check claimed file edits; resolve disagreements against source/tests/docs; reject unevidenced outputs; update `integration.md` and `state.json`. Never paste raw agent logs as the final answer.

## Verification

Choose checks by risk:

- **Low**: inspect diff; targeted test if available.
- **Medium**: targeted tests; typecheck/lint; affected build.
- **High**: full tests if practical; build; browser/CLI smoke; manual checklist; independent review pass (`vd:code-review`).

Report skipped checks honestly.

## Final answer

Keep it shorter than `final-report.md`: outcome, important files changed / artifacts created, verification run, skipped checks, remaining risk.

## References

- `references/packet-schema.md` — schema for packet, result, `orchestration.md`, and `state.json` artifacts.
- `references/approval-gates.md` — when to stop and ask vs. proceed.
- `references/execution-examples.md` — worked examples of mode choice in Claude Code.
