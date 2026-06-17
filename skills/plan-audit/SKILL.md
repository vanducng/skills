---
name: plan-audit
description: "Audit a vd:plan output for gaps, inconsistencies, missing scaffolding, and codebase drift using an independent clean-context subagent. Use after vd:plan (or any time after manual edits to phase files) when stakes warrant verification beyond same-context red-team. Auto-fires at end of vd:plan --deep."
license: MIT
argument-hint: "[plan-dir] [--fix] [--apply-all]"
metadata:
  author: vanducng
  version: "1.1.0"
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

1. **Never edit source code.** This skill only edits plan files (and only with `--fix`, only HIGH/CRITICAL findings, with per-finding confirmation by default — or single up-front confirmation when `--apply-all` is set). Never touches the actual codebase.
2. **Always use a clean-context subagent.** Inline reasoning shares the same blind spots as the author. The point of audit is independence — `Agent` tool, fresh context, plan files as the only input. Hand the subagent the plan and the goal, **not the author's argument for why the plan is sound** — withholding the claim is what keeps the second look honest. "Confirm this is right" invites agreement; "does this hold up?" invites scrutiny.
3. **Findings are advisory, not blocking.** Audit prints a report and exits. It never blocks `vd:plan` completion or `vd:cook` execution. The author decides.
4. **Only HIGH/CRITICAL are eligible for `--fix`.** MEDIUM/LOW are observational — surfacing them is the value, fixing them auto would be over-reach.
5. **Respect `decisions.md`.** If the plan dir contains `decisions.md`, listed non-goals are intentional exclusions — drop those findings entirely. "Trade-offs" entries: drop the unchosen-side findings. "Constraints accepted" entries: a finding that contradicts the constraint may surface as MEDIUM with note "constraint may need revisiting" — never CRITICAL/HIGH.
6. **Audit one plan at a time.** Multi-plan batch audit is out of scope — different plans, different contexts.

## Modes

| Mode | When | Behavior |
|---|---|---|
| **default** | Standard audit — read, spawn subagent, write report | No file edits beyond writing the report |
| `--fix` | Author wants to apply HIGH/CRITICAL findings inline | After report, walk findings interactively; per-finding y/n; edit phase file in place. **Interactive-only** — never auto-invoked by other skills. |
| `--fix --apply-all` | Author trusts the audit + wants one keypress instead of N | Print a unified preview of every HIGH/CRITICAL edit (file/line/old→new); single y/n at the top; apply the whole batch atomically on `y`. Still HIGH/CRITICAL only. **Interactive-only.** |

Detect mode from the explicit flags. `--apply-all` without `--fix` is a usage error — error out and print the help line. Announce mode in your first reply.

## Phase 1 — Resolve plan dir

- If a plan-dir path is provided as an argument → use it. Verify it exists and contains `plan.md`. If missing, error and stop.
- If no argument → check the injected Plans path for entries matching `{YYYYMMDD-HHMM}-*` or `{YYMMDD-HHMM}-*`; sort by date prefix descending, pick the most recent that contains `plan.md`. Print "Auditing most-recent plan: {path}" so the user can confirm.
- If no plan dir is found → error: "No plan dir argument and no recent plan found under the injected Plans path. Pass a path explicitly."

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
- Render report — write into the audited plan's own folder so every artifact for this feature stays grouped: `{plan-dir}/reports/`. Filename: `audit-{YYMMDD-HHMM}-{plan-slug}.md`. Date format matches the session-hook `## Naming` block (6-digit YY). `plan-slug` = the date-stripped slug of the plan dir (e.g. `260510-0938-vd-plan-audit-skill` → `vd-plan-audit-skill`). If the plan dir doesn't follow `{date}-{slug}` pattern, fall back to the dir name itself as the slug.
- If `--fix` mode (per-finding):
  - Walk findings filtered to severity in {CRITICAL, HIGH}.
  - For each, print finding + suggested fix, ask user `Apply? (y/n/skip-rest)`.
  - On `y`: open the named phase file, apply the suggested edit (Edit tool, with the user's confirmation of the exact diff if it's non-trivial). Mark finding as "applied" in the report.
  - On `n` or `skip-rest`: leave finding unfixed, note as "deferred" in the report.

- If `--fix --apply-all` mode (batch):
  - Filter findings to severity in {CRITICAL, HIGH}. If the filtered list is empty, print "No HIGH/CRITICAL findings to apply" and exit without prompting.
  - Compute the concrete edit for each finding (the exact `old_string`/`new_string` pair that the Edit tool will use). If any edit cannot be made concrete from the `suggested_fix` (ambiguous instruction, target line missing) → mark that finding `unactionable` and exclude it from the batch.
  - Print a single unified preview: for each actionable finding, show `phase-NN.md @ Lstart-Lend` + a 3-line context diff (old → new). Group by file. Cap at 60 lines total — if longer, write the full preview alongside the audit report in `{plan-dir}/reports/`, filename `audit-{date}-{slug}.preview.diff`, and print only the file/line summary inline.
  - Ask **one** prompt: `Apply N HIGH/CRITICAL edits across M files? (y/n)`. Default is `n`. No `skip-rest` — it's all-or-nothing.
  - On `y`: apply each edit in order. **If any edit fails** (file changed since audit read, `old_string` not unique, etc.) → stop, mark already-applied as `applied`, the failing one as `failed`, remaining as `deferred`. Surface the failure inline and in the report so the author can re-audit. Do **not** roll back applied edits — they're plan-file edits, not code, and partial progress is recoverable via `git`.
  - On `n`: leave all findings unfixed, note them as `deferred`. Skill exits with a one-line summary.
  - `unactionable` findings always appear in the report regardless of choice — surfacing them is the value.

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

1. **Print report path** — use an openable location such as `Audit report: [audit-report.md](/absolute/path/to/audit-report.md)` and include `file:///absolute/path/to/audit-report.md` when helpful. Do not print only the basename.
2. **Print top-3 findings inline** — sorted by severity. Just summary + phase ref. Full detail in the file.
3. **Recommend next step** based on verdict:
   - `block` → "Critical findings — revise plan before `vd:cook`."
   - `revise-before-cook` → "Address HIGH findings before execution."
   - `proceed-with-caveats` → "Plan is workable; review MEDIUM findings."
   - `proceed` → "No blocking issues. Cook when ready."
4. **If `--fix` ran**, summarize: `{N} fixes applied, {M} deferred, {U} unactionable, {F} failed.` (omit zero-count buckets).
5. **Recommend re-run** after fixes: "Re-run `vd:plan-audit` after edits to verify."

## Anti-rationalization

| Excuse | Reality |
|---|---|
| "I'll do the audit inline — it's faster" | Inline = same context = same blind spots. Use the subagent. |
| "The plan is small — skip decisions.md check" | Small plans have non-goals too. Read it if it exists. |
| "Audit found 0 issues — must be wrong" | Or the plan is good. Don't pad findings to look thorough. |
| "I'll fix MEDIUM findings too while I'm in --fix" | Out of scope. Surface, don't fix. The author decides. |
| "I'll extend `--apply-all` to MEDIUM/LOW for tidy output" | No. The trust boundary is HIGH/CRITICAL — anything below is observational. |
| "Just have another skill invoke `--apply-all` automatically" | `--apply-all` is interactive — one human keypress at the preview gate. It is NOT for auto-invocation by `vd:plan --deep` or `vd:cook --auto`. |
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

1. Announce mode (default / `--fix` / `--fix --apply-all`) and resolved plan-dir in the first reply.
2. Phase 1 (resolve) and Phase 2 (read) happen visibly — print plan dir + file count before spawning the subagent.
3. Subagent dispatch is one `Agent` tool call. Print "Spawning audit subagent..." so the user sees the boundary.
4. After subagent returns, print the report path and top-3 findings inline. Don't paste the whole report.
5. `--fix` (per-finding) walks findings interactively — one prompt per HIGH/CRITICAL.
6. `--fix --apply-all` (batch) shows one unified preview, asks one y/n, applies the batch atomically. Default-no on the prompt.
7. End with the recommended next step. Don't leave the author wondering whether to cook.

## References

- `references/audit-checklist.md` — six audit categories + severity definitions (subagent paste-target)

## Workflow position

**Typically follows:** `vd:plan` (manual run after planning), `vd:plan --deep` (auto-invoked as Phase 7)
**Typically precedes:** `vd:cook` (with HIGH/CRITICAL addressed) or another `vd:plan` revision pass
**Compares to:** `vd:plan --deep` Phase 6 (red-team) — that pass is same-context author's-eye; this pass is clean-context independent. Both useful, both cheap. Prefer audit when stakes are high or after manual edits.
