---
name: plan-audit
description: "Audit a vd:plan output for gaps, inconsistencies, missing scaffolding, and codebase drift using an independent clean-context subagent. Use after vd:plan (or any time after manual edits to phase files) when stakes warrant verification beyond same-context red-team. Auto-fires at end of vd:plan --deep."
license: MIT
argument-hint: "[plan-dir] [--fix]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Plan Audit

## What this skill is — and isn't

| Skill | Question it answers | Output |
|---|---|---|
| `vd:plan` | "Given the chosen approach, what are the steps?" | Phased plan files |
| `vd:plan --deep` Phase 6 (red-team) | "What does THIS author's plan assume that isn't true?" | Three hostile questions, same context |
| **`vd:plan-audit`** | **"Independently — does this plan hold up against the real codebase and the stated goal?"** | **Severity-tagged audit report (clean-context subagent)** |
| `vd:research` | "What do external sources say about X?" | Comparison report with citations |

The `--deep` red-team round (in `vd:plan`) lives inside the same conversation that wrote the plan — it shares the author's blind spots. **Plan-audit escapes that** by spawning a subagent with **only** the plan files + audit checklist as input. No conversation history, no author bias.

It's a **second pair of eyes**, not a redesign tool. Findings are advisory — the author still owns the plan.

## Hard rules

1. **Never edit source code.** This skill only edits plan files (and only with `--fix`, only HIGH/CRITICAL findings, only with per-finding confirmation). Never touches the actual codebase.
2. **Always use a clean-context subagent.** Inline reasoning shares the same blind spots as the author. The point of audit is independence — `Agent` tool, fresh context, plan files as the only input.
3. **Findings are advisory, not blocking.** Audit prints a report and exits. It never blocks `vd:plan` completion or `vd:cook` execution. The author decides.
4. **Only HIGH/CRITICAL are eligible for `--fix`.** MEDIUM/LOW are observational — surfacing them is the value, fixing them auto would be over-reach.
5. **Respect `decisions.md`.** If the plan dir contains `decisions.md`, listed non-goals are intentional exclusions — drop those findings entirely. "Trade-offs" entries: drop the unchosen-side findings. "Constraints accepted" entries: a finding that contradicts the constraint may surface as MEDIUM with note "constraint may need revisiting" — never CRITICAL/HIGH.
6. **Audit one plan at a time.** Multi-plan batch audit is out of scope — different plans, different contexts.

## Modes

| Mode | When | Behavior |
|---|---|---|
| **default** | Standard audit — read, spawn subagent, write report | No file edits beyond writing the report |
| `--fix` | Author wants to apply HIGH/CRITICAL findings inline | After report, walk findings interactively; per-finding y/n; edit phase file in place. **Interactive-only** — never auto-invoked by other skills. |

Detect mode from the explicit flag. Announce mode in your first reply.

## Phase 1 — Resolve plan dir

- If a plan-dir path is provided as an argument → use it. Verify it exists and contains `plan.md`. If missing, error and stop.
- If no argument → list `plans/` entries matching `{YYYYMMDD-HHMM}-*` or `{YYMMDD-HHMM}-*`, sort by date prefix descending, pick the most recent that contains `plan.md`. Print "Auditing most-recent plan: {path}" so the user can confirm.
- If no plan dir is found → error: "No plan dir argument and no recent plan found under `plans/`. Pass a path explicitly."

## Phase 2 — Read inputs

Read into the controller context (so the subagent prompt can paste them verbatim):

- `{plan-dir}/plan.md` — required
- `{plan-dir}/phase-*.md` — all phase files
- `{plan-dir}/decisions.md` — optional. If present, pass to subagent as the "non-goals / out-of-scope" block.
- `{plan-dir}/research/*.md` — optional. If present, summarize paths only (not full content) for the subagent's awareness.
- `{plan-dir}/reports/*.md` — optional. Same — paths only.

If `decisions.md` is absent, treat as "no exclusions stated."

## Phase 3 — Spawn audit subagent

Use the `Agent` tool with `subagent_type: general-purpose`. Single subagent, full plan context. **Do not** spawn N parallel agents — plans are small (5-10 phase files, ~5K tokens) and an independent voice across the whole plan is the goal.

### Subagent prompt template

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

NEGATIVE EXAMPLE: if decisions.md says "no auth — internal tool only", do
NOT add a CRITICAL finding "missing auth phase". The author already decided.

# Audit checklist
{paste contents of references/audit-checklist.md}

# Codebase root
{repo-root-path}

You may use Read/Glob/Grep tools to:
- Re-Read each phase file directly so `line_range` numbers are real, not fabricated.
  (The verbatim contents above are for context; cite line numbers from your own Read calls.)
- Spot-check codebase reality (does file X exist? does the naming convention match?).
Do not read more than ~20 files total — this is a survey, not deep analysis.

# Your task
1. Walk the audit checklist (6 categories) against the plan.
2. For each finding, classify severity: CRITICAL / HIGH / MEDIUM / LOW (defs
   in checklist).
3. For each finding, name: phase number, line range (best-effort), one-line
   summary, suggested fix.
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

## Phase 4 — Apply findings

- Parse subagent JSON output. Validate shape; if malformed, ask the subagent to retry once.
- Render report to `plans/reports/audit-{YYMMDD-HHMM}-{plan-slug}.md` using the report template below. Date format matches the session-hook `## Naming` block (6-digit YY). `plan-slug` = the date-stripped slug of the plan dir (e.g. `260510-0938-vd-plan-audit-skill` → `vd-plan-audit-skill`). If the plan dir doesn't follow `{date}-{slug}` pattern, fall back to the dir name itself as the slug.
- If `--fix` mode:
  - Walk findings filtered to severity in {CRITICAL, HIGH}.
  - For each, print finding + suggested fix, ask user `Apply? (y/n/skip-rest)`.
  - On `y`: open the named phase file, apply the suggested edit (Edit tool, with the user's confirmation of the exact diff if it's non-trivial). Mark finding as "applied" in the report.
  - On `n` or `skip-rest`: leave finding unfixed, note as "deferred" in the report.

### Report template

```markdown
---
title: "Plan Audit — {plan-title}"
date: {YYYY-MM-DD}
auditor: plan-audit-subagent
plan: ../{plan-dir-name}/
verdict: {recommended_action} — {verdict_one_liner}
---

# Plan Audit: {plan-title}

## Summary
- {N} findings: {C} critical · {H} high · {M} medium · {L} low
- Recommended action: **{block | revise-before-cook | proceed-with-caveats | proceed}**
- {one-line verdict}

## Findings (severity-sorted)

### CRITICAL
- **{summary}** — phase {N}, {line range} — {detail}
  → fix: {suggested fix}
  → status: {advisory | applied | deferred}

### HIGH
- ...

### MEDIUM
- ...

### LOW
- ...

## Decisions respected
- {non-goal from decisions.md that the audit honored, if any}

## Files inspected
- {list of plan files read}
- {list of codebase files spot-checked, if any}
```

## Phase 5 — Hand off

After writing the report:

1. **Print report path** — `Audit report: plans/reports/audit-{date}-{slug}.md`
2. **Print top-3 findings inline** — sorted by severity. Just summary + phase ref. Full detail in the file.
3. **Recommend next step** based on verdict:
   - `block` → "Critical findings — revise plan before `vd:cook`."
   - `revise-before-cook` → "Address HIGH findings before execution."
   - `proceed-with-caveats` → "Plan is workable; review MEDIUM findings."
   - `proceed` → "No blocking issues. Cook when ready."
4. **If `--fix` ran**, summarize: `{N} fixes applied, {M} deferred.`
5. **Recommend re-run** after fixes: "Re-run `vd:plan-audit` after edits to verify."

## Anti-rationalization

| Excuse | Reality |
|---|---|
| "I'll do the audit inline — it's faster" | Inline = same context = same blind spots. Use the subagent. |
| "The plan is small — skip decisions.md check" | Small plans have non-goals too. Read it if it exists. |
| "Audit found 0 issues — must be wrong" | Or the plan is good. Don't pad findings to look thorough. |
| "I'll fix MEDIUM findings too while I'm in --fix" | Out of scope. Surface, don't fix. The author decides. |
| "Just block on CRITICAL by default" | Audit is advisory. The author owns the call. |
| "I'll re-read the plan in main context to double-check" | That defeats the point. Trust the subagent's report. |

## Quality bar

- **Independent.** Audit subagent has no parent conversation context. No author bias.
- **Severity-honest.** A CRITICAL is "plan will fail at cook." A HIGH is "plan succeeds but produces a flawed result." Don't inflate.
- **Concrete.** Every finding names a phase, ideally a line range, and a suggested fix. "Plan is vague" is not a finding. "Phase 3 step 4 says 'add validation' without naming the validator" is.
- **Decisions-aware.** Listed non-goals don't show up as gaps. The audit respects what was already decided.
- **Re-runnable.** Author can fix → re-run → see fewer findings. The skill is composable, not one-shot.

## Specials

- **Migration plans** — audit specifically checks: rollback path tested? consumers updated after migration? feature flag for staged rollout? If any missing → HIGH.
- **API breaking changes** — audit checks the "add new → migrate callers → remove old" sequence is explicit (not collapsed). If collapsed → HIGH.
- **Performance plans** — audit checks for baseline numbers in phase 1 + comparison evidence in success criteria. Missing → HIGH.
- **Library upgrades** — audit checks each phase ends with smoke test of an affected feature. Missing → MEDIUM.
- **Bug fixes** — audit checks for a failing-test-first step. Missing → MEDIUM.
- **Plans with no `decisions.md`** — audit emits a LOW advisory: "Consider adding decisions.md to record explicit non-goals — reduces false positives on re-audit."

## Output rules

1. Announce mode (default / `--fix`) and resolved plan-dir in the first reply.
2. Phase 1 (resolve) and Phase 2 (read) happen visibly — print plan dir + file count before spawning the subagent.
3. Subagent dispatch is one `Agent` tool call. Print "Spawning audit subagent..." so the user sees the boundary.
4. After subagent returns, print the report path and top-3 findings inline. Don't paste the whole report.
5. `--fix` walks findings interactively — one prompt per HIGH/CRITICAL, no batch yes-to-all.
6. End with the recommended next step. Don't leave the author wondering whether to cook.

## References

- `references/audit-checklist.md` — six audit categories + severity definitions (subagent paste-target)

## Workflow position

**Typically follows:** `vd:plan` (manual run after planning), `vd:plan --deep` (auto-invoked as Phase 7)
**Typically precedes:** `vd:cook` (with HIGH/CRITICAL addressed) or another `vd:plan` revision pass
**Compares to:** `vd:plan --deep` Phase 6 (red-team) — that pass is same-context author's-eye; this pass is clean-context independent. Both useful, both cheap. Prefer audit when stakes are high or after manual edits.
