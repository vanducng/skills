# Plan audit (`vd:plan --audit`)

Independent clean-context check of a plan against the real codebase and the stated goal. The `--deep` red-team round shares the author's blind spots; this pass escapes that.

Findings are advisory. The author owns the plan. Never edits source code. Plan files change only with `--fix`, and only HIGH/CRITICAL findings.

## Modes

| Mode | Behavior |
|---|---|
| `--audit` | Read, spawn subagent, write report |
| `--audit --fix` | After the report, walk HIGH/CRITICAL interactively |
| `--audit --fix --apply-all` | One preview, one y/n, apply the HIGH/CRITICAL batch |

`--apply-all` without `--fix` is a usage error. `--fix` is interactive-only - never auto-invoked by `--deep` or `vd:cook --auto`.

## Hard rules

1. **Always a clean-context subagent.** Hand the plan and the goal, not the author's argument for why it is sound.
2. **Respect `decisions.md`.** Listed non-goals are exclusions. Trade-off unchosen sides are dropped. Constraints: at most MEDIUM.
3. **One plan at a time.**
4. **Only HIGH/CRITICAL are eligible for `--fix`.**

## Workflow

### 1. Resolve plan dir

Argument path with `plan.md`, or the most recent `{YYYYMMDD-HHMM}-*` / `{YYMMDD-HHMM}-*` under the injected Plans path. Print the path. None found → stop.

### 2. Read

`plan.md`, all `phase-*.md`, optional `decisions.md` (verbatim), optional `research/` and `reports/` (paths only).

### 3. Spawn the auditor

One `Agent` (`general-purpose`). Other runtimes: that host's subagent or a fresh `codex exec`. Degraded inline pass only when no isolation exists - say so.

Paste [`audit-checklist.md`](audit-checklist.md) verbatim. Keep the output schema minimal (`summary`, `findings`). Prompt shape:

```
You are an independent plan auditor. You have NO access to the prior conversation.
Inputs: the plan files + the audit checklist + (if present) decisions.md.

Return ONLY JSON:
{
  "summary": {
    "counts": {"critical": N, "high": N, "medium": N, "low": N},
    "recommended_action": "block | revise-before-cook | proceed-with-caveats | proceed",
    "verdict_one_liner": "..."
  },
  "findings": [
    {
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "category": "consistency|codebase-drift|missing-scaffolding|unrealistic-criteria|deps-sequencing|scope-shape",
      "phase": "plan|N",
      "line_range": "L42-L48",
      "summary": "one-line gist",
      "detail": "1-3 sentences",
      "suggested_fix": "concrete edit"
    }
  ]
}
```

### 4. Report and optional fix

Write `{plan-dir}/reports/audit-{YYMMDD-HHMM}-{plan-slug}.md`. Print the path and the top-3 findings.

`--fix`: per HIGH/CRITICAL, `Apply? (y/n/skip-rest)`.
`--fix --apply-all`: unified preview, one y/n, default `n`. Stop on the first failed edit; do not roll back.

Verdicts: `block` / `revise-before-cook` / `proceed-with-caveats` / `proceed`. Recommend re-running `--audit` after edits.

## Specials

- Migration: rollback tested? consumers after migration? flag for staged rollout? Missing → HIGH.
- API break: add → migrate callers → remove old must be explicit. Collapsed → HIGH.
- Perf: baseline in phase 1 + comparison evidence. Missing → HIGH.
- Upgrade: each phase ends with a smoke of a touched feature. Missing → MEDIUM.
- Bug fix: failing-test-first step. Missing → MEDIUM.
- No `decisions.md`: LOW advisory.
