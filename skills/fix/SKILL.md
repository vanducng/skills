---
name: fix
description: "Fix issues end-to-end across data pipelines (Airflow/dbt), app stack (backend/frontend), and infra (CI/CD, Terraform, K8s). Scout → diagnose → apply at root cause → verify with fresh evidence → add regression guard. Use for failing DAGs, dbt test failures, 5xx, UI regressions, GH Actions failures, terraform drift, CrashLoopBackOff, lint/type errors. Stops after 3 failed attempts to question architecture."
license: MIT
argument-hint: "[issue description] [--quick | --auto] [--no-prevent]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Fix

End-to-end fixing across the surfaces you actually work on: data pipelines, app stack, infra. Find the cause first, fix at the source, verify with fresh evidence, leave a regression guard so the same class of bug can't return.

## Iron law

```
NO FIX WITHOUT ROOT CAUSE. NO "DONE" WITHOUT FRESH EVIDENCE.
```

Symptom fixes are failure. Random changes waste time and create new bugs. Three failed attempts means the approach is wrong — stop and question architecture, don't keep trying.

## When to use

| Surface | Triggers |
|---|---|
| **Data pipeline** | DAG/task failures, retry loops, dbt test failures, schema drift, freshness alerts, incremental/snapshot breakage, late or missing data |
| **App backend** | 5xx, panics, deploy failures, failed migrations, env-var/secret mismatch, integration regressions |
| **App frontend** | UI bug, weird behavior, hydration error, build failure, browser-specific regression, broken interaction |
| **CI/CD** | failing GH Actions / pipeline jobs, flaky tests, build-matrix gaps, deploy gate failures, secret/env config drift |
| **Terraform / IaC** | plan errors, apply failures, state drift, provider auth, cyclic deps, partial resources |
| **K8s / cloud** | CrashLoopBackOff, OOMKill, image pull errors, networking/policy denial, secret rotation |
| **Code-local** | type errors, lint issues, test failures, exceptions traced to a known file |

## Anti-patterns — stop if you catch yourself thinking this

| Thought | Reality |
|---|---|
| "I see the problem, let me just fix it" | Symptoms ≠ cause. Scout + diagnose first. |
| "Quick patch now, investigate later" | "Later" never comes. Fix at source. |
| "Just try changing X, see if it works" | Guess-and-check is slower than systematic diagnosis. |
| "It's probably X" | "Probably" = guessing. Evidence first. |
| "One more attempt" (after 2 failures) | 3+ failures = wrong approach. Question architecture. |
| "Tests pass, ship it" | Without a regression guard, the same bug class returns. |
| "Pod is running, must be fixed" | Running ≠ working. Verify the actual workload. |
| "Pipeline succeeded once, must've been flaky" | Reproduce or pin the cause before closing. |

## Modes

| Mode | When | Behavior |
|---|---|---|
| **default** | Standard issue, you want it done right | Full loop: scout → diagnose → apply → verify → prevent. Pauses for confirmation if the fix touches >3 files or crosses surfaces. |
| `--quick` | Trivial (lint, single type error, obvious typo, known recipe) | Skip deep diagnosis. Still verify with fresh evidence. Still add regression test if behavior changed. |
| `--auto` | You trust the loop, end-to-end run | No confirmation gates. Stops only on verification failure or 3rd failed attempt. |
| `--no-prevent` | Throwaway / spike / hotfix where guard will land in follow-up | Skip regression-test step. Loud warning. Use sparingly. |

Detect mode from the argument; announce in your first reply.

## Workflow

```
[issue]
  │
  ▼
1. Scout            ── locate affected code/models/manifests (/vd:scout or 2-3 Explore agents)
  │
  ▼
2. Diagnose         ── activate /vd:debug; structured root-cause analysis; capture pre-fix evidence
  │
  ▼
3. Assess scope     ── quick | standard | deep | parallel; decide how much process is warranted
  │
  ▼
4. Pick playbook    ── data-pipeline | app-stack | infra | generic
  │
  ▼
5. Apply fix        ── at root cause, minimal change, existing patterns
  │
  ▼
6. Verify + prevent ── exact rerun; blast-radius sweep; regression guard; contract check
  │
  ▼
7. Finalize         ── report; offer commit via /vd:ship or git; offer /vd:journal
```

### 1. Scout (mandatory)

- Activate `/vd:scout` OR launch 2–3 parallel `Explore` subagents.
- Discover: project type/language/framework, affected files/models/manifests, direct callers/dependents, related tests, recent git changes (`git log -p -- <path>`), and local patterns for similar fixes.
- Read `./docs` if the project is unfamiliar.
- **Quick mode:** just locate the file(s) + immediate deps.
- If you need to ask a clarifying question, ask it after this scan and ground it in concrete files, logs, commits, or functions you found.

Output: `✓ Scouted — N files, M deps, K tests`

### 2. Diagnose (mandatory)

**Activate `/vd:debug`** for systematic-debugging + root-cause-tracing. Don't restate the debug skill here — call it. Use `references/diagnosis-protocol.md` when the cause is not immediately proven.

Required outputs from this step:
- **Pre-fix evidence captured**: exact error, failing command, stack trace, log snippet, dbt run-results, kubectl events, `terraform plan` output — whatever applies. This is the baseline for Step 5.
- **Confirmed root cause** with an evidence chain (not just a hypothesis).
- **Root-cause checklist** in concrete sentences:
  - Exact symptom: copy the precise error/failing assertion/observed behavior.
  - Reproduction: minimal command, input, environment, or workflow that triggers it.
  - Expected vs actual: what should happen, and what does happen.
  - Root cause: the specific line, missing guard, race, contract violation, bad data shape, or design flaw.
  - Why now: recent commit, dependency/env change, data shape, timing, or load condition that exposed it.
  - Blast radius: callers, downstream models, user flows, jobs, resources, or public contracts sharing the same cause.
- **Scope**: which files/models/resources need to change, and which dependent paths must be checked for side effects.

If 2+ hypotheses fail → broaden context, re-scout, consider that the *real* cause is upstream/downstream of where the symptom appears.

If you can't get to a confirmed cause in reasonable time → STOP, report what you tried, ask the user.

Output: `✓ Diagnosed — root cause: …, evidence: …, scope: N files`

### 3. Assess scope

Classify the fix after scouting and diagnosis, then choose how much workflow to run:

| Scope | Indicators | Behavior |
|---|---|---|
| **Quick** | Single file, clear type/lint/syntax error, root cause obvious from evidence | Minimal scout + diagnose; exact rerun; type/lint/build verification as relevant. |
| **Standard** | 2–5 files, user-visible bug, test failure, multi-step but local cause | Full loop: playbook, fix, adjacent tests, blast-radius sweep, regression guard. |
| **Deep** | 5+ files, architecture/design impact, perf/security risk, data/infra cross-surface issue | Pause before broad changes unless `--auto`; consider `/vd:brainstorm` or `/vd:plan`; verify across every affected surface. |
| **Parallel** | 2+ independent issues or independent affected surfaces | Split by issue/surface, diagnose separately, then run integration verification once all fixes land. |

### 4. Pick playbook

Match the surface; load the matching reference. If multiple surfaces apply (e.g. a dbt model failure caused by a Terraform-managed warehouse role), use both. Load lazily — don't preload all playbooks.

| Surface | Reference |
|---|---|
| Airflow DAG / dbt model / data freshness | `references/playbook-data-pipeline.md` |
| Backend service / API / frontend UI | `references/playbook-app-stack.md` |
| CI/CD / Terraform / K8s | `references/playbook-infra.md` |
| Doesn't fit cleanly | `references/playbook-generic.md` |

### 5. Apply fix

See `references/apply-fix.md`. Highlights:
- Fix the **root cause**, not the symptom.
- **Minimal diff.** No drive-by refactors. No "while I'm here" cleanup.
- Follow existing patterns in the affected module.
- Compile / type-check / lint after each file, not at the end.

### 6. Verify + prevent (mandatory)

See `references/verify-and-prevent.md`. Highlights:
- **Verify with fresh evidence**: rerun the EXACT failing command from Step 2. Compare output. No claims without showing the rerun.
- **Side-effect sweep**: run tests/checks for modified files plus transitively affected modules or downstream resources from the blast-radius list. Manually walk critical flows when no automated check exists.
- **Contract check**: confirm public API contracts, exported function signatures/types, response shapes, DB schemas, metric definitions, env vars, Terraform outputs, and job/DAG schedules are unchanged — or call out the intentional change and migration path.
- **Regression test**: add or update a test/check that fails without the fix and passes with it. dbt → add or fix a test; Airflow → add a sensor / assertion; Terraform → add a `terraform validate`/CI guardrail; backend → unit + integration; frontend → component test + e2e if the bug was reachable from the UI.
- **Defense-in-depth**: where applicable, add a guard at a layer above the bug (schema constraint, type narrowing, K8s probe, CI check) so the same class can't recur silently.
- **Verification loop**: if it fails, back to Step 2. After **3 failed verification cycles → stop and question architecture**, surface to user.

Output: `✓ Verified + prevented — before/after attached, N tests added, M guards added`

### 7. Finalize

1. Print a compact report: confidence, root cause, files touched, evidence summary, regression-guard summary.
2. Update `./docs` only if the change affects shared docs (codebase-summary / architecture / standards). Skip otherwise.
3. Offer to commit/PR via `/vd:ship` (full pipeline) or a single conventional commit via `git`/`git-manager`.
4. Offer `/vd:journal` for a focused post-mortem entry if the fix was non-trivial or the root cause was surprising.

## Tool integration

- **Database** — `psql` (Postgres), `bq` (BigQuery), `sqlit` CLI for any saved connection
- **CI/CD** — `gh run view --log-failed`, `gh pr checks`
- **K8s** — `kubectl logs --previous`, `describe`, `get events --sort-by=.lastTimestamp`
- **Terraform** — `terraform plan -refresh-only`, state-list, targeted apply (carefully)
- **dbt** — `dbt run --select`, `dbt test`, `target/run_results.json`, `target/manifest.json`
- **Airflow** — task logs (UI), `airflow tasks logs`, scheduler logs, `airflow tasks clear` for backfill
- **Tracing** — APM (Datadog, Sentry), OpenTelemetry
- **Secrets** — `sops -d` for infra repo (age key per `.mise.toml`); never paste decrypted contents into reports/commits
- **Frontend verification** — Chrome MCP / `ck:chrome-devtools` to confirm UI fix
- **Skills:** `/vd:debug` (Step 2), `/vd:scout` (Step 1), `/vd:research` (unknown libs/CVEs surfaced mid-fix), `/vd:gopass` (creds)

## Workflow position

**Typically follows:** `/vd:debug` (when diagnosis was done separately), `/vd:scout` (after locating code)
**Typically precedes:** `/vd:ship` (ship the fix), `/vd:journal` (post-fix log)
**Related:** `/vd:cook` (feature execution, not bug-driven), `/vd:brainstorm` (when the fix exposes a design problem)

## References (load on demand)

| Reference | Load when |
|---|---|
| `references/diagnosis-protocol.md` | Step 2; cause is not immediately proven |
| `references/apply-fix.md` | About to make code/config changes |
| `references/verify-and-prevent.md` | Step 6; always |
| `references/playbook-data-pipeline.md` | Airflow / dbt / freshness / schema drift |
| `references/playbook-app-stack.md` | Backend service, API, frontend, deploy |
| `references/playbook-infra.md` | CI/CD, Terraform, K8s, secrets |
| `references/playbook-generic.md` | Issue doesn't fit a specific playbook |
