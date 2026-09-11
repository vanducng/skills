---
name: fix
description: "Fix issues end-to-end across data pipelines (Airflow/dbt), app stack (backend/frontend), and infra (CI/CD, Terraform, K8s). Scout → diagnose → apply at root cause → verify with fresh evidence → add regression guard. Use for failing DAGs, dbt test failures, 5xx, UI regressions, GH Actions failures, terraform drift, CrashLoopBackOff, lint/type errors. Stops after 3 failed attempts to question architecture."
license: MIT
argument-hint: "[issue description] [--quick | --auto] [--no-prevent]"
metadata:
  author: vanducng
  version: "1.2.0"
---

# Fix

End-to-end fixing across the surfaces you actually work on: data pipelines, app stack, infra. Find the cause first, fix at the source, verify with fresh evidence, leave a regression guard so the same class of bug can't return.

## Iron law

```
NO FIX WITHOUT ROOT CAUSE. NO "DONE" WITHOUT FRESH EVIDENCE.
```

Symptom fixes are failure. Random changes waste time and create new bugs. Three failed attempts means the approach is wrong - stop and question architecture, don't keep trying.

## Modes

| Mode | When | Behavior |
|---|---|---|
| **default** | Standard issue, you want it done right | Full loop: scout → diagnose → apply → verify → prevent. Pauses for confirmation if the fix touches >3 files or crosses surfaces. |
| `--quick` | Trivial (lint, single type error, obvious typo, known recipe) | Skip deep diagnosis. Still verify with fresh evidence. Still add regression test if behavior changed. |
| `--auto` | You trust the loop, end-to-end run | No confirmation gates. Stops only on verification failure or 3rd failed attempt. |
| `--no-prevent` | Throwaway / spike / hotfix where guard will land in follow-up | Skip regression-test step. Loud warning. Use sparingly. |

Detect mode from the argument; announce in your first reply.

## Workflow

1. **Scout** - locate affected code/models/manifests (`vd:scout` or 2-3 Explore agents)
2. **Diagnose** - activate `vd:debug`; structured root-cause analysis; capture pre-fix evidence
3. **Assess scope** - quick | standard | deep | parallel; decide how much process is warranted
4. **Pick playbook** - data-pipeline | app-stack | infra | generic
5. **Apply fix** - at root cause, minimal change, existing patterns
6. **Verify + prevent** - exact rerun; blast-radius sweep; regression guard; contract check
7. **Finalize** - report; offer commit via `vd:ship` or git; offer `vd:journal`

### 1. Scout (mandatory)

- Activate `vd:scout` OR launch 2-3 parallel `Explore` subagents.
- Discover: project type/language/framework, affected files/models/manifests, direct callers/dependents, related tests, recent git changes (`git log -p -- <path>`), and local patterns for similar fixes.
- Read `./docs` if the project is unfamiliar.
- **Quick mode:** just locate the file(s) + immediate deps.
- **Scout before questions.** Always scan the codebase BEFORE asking anything. State a 3-6 bullet codebase-context summary first (project type/stack, the symptom file + its callers, related tests, the suspect recent commit). Only then ask a clarifying question - grounded in concrete files, logs, commits, or functions you found. Never ask what the scan already answers.

Output: `✓ Scouted - N files, M deps, K tests`

### 2. Diagnose (mandatory)

**Activate `vd:debug`** - its `systematic-debugging` and `root-cause-tracing` references are the diagnosis method. Don't restate them here - call them.

Required outputs from this step:

- **Pre-fix evidence captured**: exact error, failing command, stack trace, log snippet, dbt run-results, kubectl events, `terraform plan` output - whatever applies. This is the baseline for Step 6's rerun.
- **Confirmed root cause** with an evidence chain (not just a hypothesis), including why-now and blast radius.
- **Scope**: which files/models/resources need to change, and which dependent paths must be checked for side effects.

If 2+ hypotheses fail → broaden context, re-scout, consider that the *real* cause is upstream/downstream of where the symptom appears.

If you can't get to a confirmed cause in reasonable time → STOP, report what you tried, ask the user.

Output: `✓ Diagnosed - root cause: …, evidence: …, scope: N files`

### 3. Assess scope

Classify the fix after scouting and diagnosis, then choose how much workflow to run:

| Scope | Indicators | Behavior |
|---|---|---|
| **Quick** | Single file, clear type/lint/syntax error, root cause obvious from evidence | Minimal scout + diagnose; exact rerun; type/lint/build verification as relevant. |
| **Standard** | 2-5 files, user-visible bug, test failure, multi-step but local cause | Full loop: playbook, fix, adjacent tests, blast-radius sweep, regression guard. |
| **Deep** | 5+ files, architecture/design impact, perf/security risk, data/infra cross-surface issue | Pause before broad changes unless `--auto`; consider `vd:brainstorm` or `vd:plan`; verify across every affected surface. |
| **Parallel** | 2+ independent issues or independent affected surfaces | Split by issue/surface, diagnose separately, then run integration verification once all fixes land. |

### 4. Pick playbook

Match the surface; load the matching reference. If multiple surfaces apply (e.g. a dbt model failure caused by a Terraform-managed warehouse role), use both. Load lazily - don't preload all playbooks.

| Surface | Reference |
|---|---|
| Airflow DAG / dbt model / data freshness | `references/playbook-data-pipeline.md` |
| Backend service / API / frontend UI | `references/playbook-app-stack.md` |
| CI/CD / Terraform / K8s | `references/playbook-infra.md` |
| Doesn't fit cleanly | `references/playbook-generic.md` |

### 5. Apply fix

See `references/apply-fix.md`: fix the root cause not the symptom, minimal diff, follow existing patterns, compile / type-check / lint after each file.

### 6. Verify + prevent (mandatory)

See `references/verify-and-prevent.md`: rerun the exact failing command and compare against the baseline, sweep the blast radius, check public contracts, add a regression guard, and stop hard if the sweep finds a regression. 3 failed verification cycles → stop and question architecture.

**CI failures - reproduce the check locally before re-pushing.** A red GH Actions job is not a debugger: pushing a guess to watch CI is a slow, public loop. Pull the failing job (`gh run view <run-id> --log-failed`), then reproduce and fix locally by failure type:

| Failure | Local loop before re-push |
|---|---|
| lint / format | run the repo's lint/format with `--fix`; re-run clean |
| type error | read the exact location from the log; fix; `tsc --noEmit` / `mypy` / `go vet` locally |
| test | reproduce the named test locally (drop to `vd:debug`); green locally before pushing |
| build | match CI's Node/Go/Python version + flags; reproduce the build locally |
| flake (passes on re-run, no code cause) | re-enqueue once; if it re-fails, treat as real |

Only push once the same check passes on your machine. This closes the loop that would otherwise need a standalone CI skill.

Output: `✓ Verified + prevented - before/after attached, N tests added, M guards added`

### 7. Finalize

1. Print a compact report: confidence, root cause, files touched, evidence summary, regression-guard summary.
2. Update `./docs` only if the change affects shared docs (codebase-summary / architecture / standards). Skip otherwise.
3. Offer to commit/PR via `vd:ship` (full pipeline) or a single conventional commit via `git`/`git-manager`.
4. Offer `vd:journal` for a focused post-mortem entry if the fix was non-trivial or the root cause was surprising.

## Tool integration

- **Database** - `psql` (Postgres), `bq` (BigQuery), `miudb query run --connection <conn>` for any saved connection (see `vd:miudb`; do not use `sqlit`)
- **CI/CD** - `gh run view --log-failed`, `gh pr checks`
- **K8s** - `kubectl logs --previous`, `describe`, `get events --sort-by=.lastTimestamp`
- **Terraform** - `terraform plan -refresh-only`, state-list, targeted apply (carefully)
- **dbt** - `dbt run --select`, `dbt test`, `target/run_results.json`, `target/manifest.json`
- **Airflow** - task logs (UI), `airflow tasks logs`, scheduler logs, `airflow tasks clear` for backfill
- **Tracing** - APM (Datadog, Sentry), OpenTelemetry
- **Secrets** - `sops -d` for infra repo (age key per `.mise.toml`); never paste decrypted contents into reports/commits
- **Frontend verification** - Chrome MCP / `vd:web-e2e` (persistent-profile browser + trace evidence) to confirm UI fix
- **Skills:** `vd:debug` (Step 2), `vd:scout` (Step 1), `vd:research` (unknown libs/CVEs surfaced mid-fix), `vd:gopass` (creds)
