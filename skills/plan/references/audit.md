# Independent plan audit (`vd:plan --audit`)

An independent, clean-context second look at a finished plan. The red-team round (`--deep` Phase 6) lives inside the conversation that wrote the plan and shares the author's blind spots; the audit escapes that by spawning a subagent whose **only** inputs are the plan files + the checklist. It's a second pair of eyes, not a redesign tool - findings are advisory, the author owns the plan.

## Hard rules

1. **Never edit source code.** Audit only edits plan files, only with `--fix`, only HIGH/CRITICAL findings, with confirmation.
2. **Always use a clean-context subagent.** Hand it the plan and the goal, **not the author's argument for why the plan is sound** - "does this hold up?" invites scrutiny; "confirm this is right" invites agreement. If the runtime has no subagent mechanism, fall back to a documented inline pass with fresh eyes and say so.
3. **Findings are advisory, never blocking.** Audit prints a report and exits.
4. **Respect `decisions.md`.** Listed non-goals are intentional exclusions - drop those findings. Trade-off entries: drop the unchosen-side findings. Accepted constraints: at most MEDIUM with "constraint may need revisiting."
5. **Only HIGH/CRITICAL are eligible for `--fix`.** MEDIUM/LOW are observational.

## Procedure

1. **Resolve the plan dir** (argument, or most recent `{date}-*` under the injected Plans path containing `plan.md`). Print which.
2. **Read inputs**: `plan.md` (required), all `phase-*.md`, `decisions.md` if present.
3. **Spawn one subagent** (`Agent` tool, `subagent_type: general-purpose`) with the prompt below. One subagent for the whole plan - an independent voice across all of it is the goal.
4. **Write the report** to `{plan-dir}/reports/audit-{YYMMDD-HHMM}-{plan-slug}.md` using the report template below.
5. **Surface inline**: report path (openable link), top-3 findings by severity, and the recommended next step (`block` → revise before cook; `revise-before-cook` → address HIGH first; `proceed-with-caveats` / `proceed`).
6. **`--fix`** (interactive only, never auto-invoked): walk HIGH/CRITICAL findings, per-finding y/n, apply the suggested edit to the named phase file, mark applied/deferred in the report. With `--apply-all`: one unified preview, one y/n (default no), apply the batch; on any edit failure stop and mark applied/failed/deferred - no rollback, plan files are git-recoverable.

## Subagent prompt template

```
You are an independent plan auditor. You have NO access to the prior conversation.
Your only inputs are the plan files below + the audit checklist + (if present) decisions.md.
Treat the plan as the only source of truth about intent.

# Plan dir
{plan-dir-path}

# plan.md
{verbatim contents}

# Phase files
{verbatim contents of each phase-XX-*.md}

# decisions.md (if present)
{verbatim contents}
If a "Non-goals" item appears here, it is an intentional exclusion. Do NOT
report it as a gap. If a "Trade-offs" item lists chosen vs unchosen, do NOT
flag the unchosen alternative.

NEGATIVE EXAMPLE: if decisions.md says "no auth - internal tool only", do
NOT add a CRITICAL finding "missing auth phase". The author already decided.

# Audit checklist
{paste contents of references/audit-checklist.md}

# Codebase root
{repo-root-path}

You may use Read/Glob/Grep tools to:
- Re-Read each phase file directly so `line_range` numbers are real, not fabricated.
- Spot-check codebase reality (does file X exist? does the naming convention match?).
Do not read more than ~20 files total - this is a survey, not deep analysis.

# Your task
1. Walk the audit checklist (6 categories) against the plan.
2. Classify each finding: CRITICAL / HIGH / MEDIUM / LOW (defs in checklist).
3. For each finding: phase number, line range (best-effort), one-line summary, suggested fix.
4. Skip findings that decisions.md already covers as non-goals.
5. Recommended action: block | revise-before-cook | proceed-with-caveats | proceed
6. Return ONLY a single JSON object with keys `summary` and `findings`. Shape:

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
      "line_range": "L42-L48 (best effort, omit if unknown)",
      "summary": "one-line gist",
      "detail": "1-3 sentences explaining the gap",
      "suggested_fix": "concrete edit the author can apply"
    }
  ]
}

If you find NO issues, return the same wrapper with empty findings array and
verdict "proceed". Do not pad. Do not invent gaps to look thorough.
```

## Report template

```markdown
---
title: "Plan Audit - {plan-title}"
date: {YYYY-MM-DD}
auditor: plan-audit-subagent
plan: ../{plan-dir-name}/
verdict: {recommended_action} - {verdict_one_liner}
---

# Plan Audit: {plan-title}

## Summary
- {N} findings: {C} critical · {H} high · {M} medium · {L} low
- Recommended action: **{block | revise-before-cook | proceed-with-caveats | proceed}**
- {one-line verdict}

## Findings (severity-sorted)

### CRITICAL
- **{summary}** - phase {N}, {line range} - {detail}
  → fix: {suggested fix}
  → status: {advisory | applied | deferred}

### HIGH / MEDIUM / LOW
- ...

## Decisions respected
- {non-goal from decisions.md that the audit honored, if any}

## Files inspected
- {plan files read; codebase files spot-checked}
```

## Severity honesty

A CRITICAL is "plan will fail at cook." A HIGH is "plan succeeds but produces a flawed result." Don't inflate; don't pad findings to look thorough - zero findings and verdict `proceed` is a valid, common outcome.

## Domain-specific checks

- **Migrations** - rollback path tested? consumers updated after? staged rollout? Missing → HIGH.
- **API breaking changes** - "add new → migrate callers → remove old" explicit, not collapsed? Collapsed → HIGH.
- **Performance plans** - baseline numbers in phase 1 + comparison evidence in criteria? Missing → HIGH.
- **Library upgrades** - each phase ends with a smoke test of an affected feature? Missing → MEDIUM.
- **Bug fixes** - failing-test-first step present? Missing → MEDIUM.
