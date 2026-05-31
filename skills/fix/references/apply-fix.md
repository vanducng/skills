# Apply fix

You arrived here with a **confirmed root cause** (from Step 2 / `vd:debug`). This page is about turning that into a minimal, correct change.

## Principles

1. **Fix at the source.** If bad data is written upstream, don't paper over it downstream. If a contract was violated by the caller, don't broaden the callee.
2. **Minimal diff.** Change only what the root cause requires. No drive-by refactors, no rename-while-you're-here, no opportunistic dependency bumps.
3. **Follow existing patterns.** Match the surrounding module: error handling, logging, naming, config conventions. If the surrounding pattern is wrong, leave that for a follow-up — note it, don't conflate it.
4. **Reversibility first.** Prefer the smaller, easier-to-revert version of the fix when two options work.
5. **Compile / type-check after each file.** Catching a typo one file later is 10× cheaper than 5 files later. Frontend / backend / dbt / terraform all have cheap local validation — use it.

## Per-surface notes

### Data pipeline (Airflow / dbt)
- For Airflow: prefer fixing the **task code or upstream contract**, not "rerun + clear" as a fix. Reruns are for verification, not solutions.
- For dbt: prefer fixing the **model SQL or test definition**, not loosening a test threshold. If a test is genuinely wrong, change the test in the same PR with a comment explaining why.
- Beware idempotency: incremental models, snapshots, and Airflow tasks may need a **catch-up backfill** after the fix. Plan it explicitly; don't assume the next scheduled run will heal history.
- Schema changes: coordinate with downstream consumers (BI, exposures). Use `dbt list --select state:modified+` to find blast radius.

### App stack (backend / frontend)
- Backend: if the bug is in a hot path, do the fix as a small, well-tested change first; performance tuning is a separate PR.
- Migrations: never edit a migration that has been applied to any environment beyond local. Add a new migration that corrects forward.
- Frontend: prefer the fix that survives a full reload (don't lean on in-memory state). For hydration bugs, fix the data shape mismatch — not the render-twice symptom.

### Infra (CI/CD / Terraform / K8s)
- Terraform: if state drift is the root cause, decide consciously between **`terraform apply`** (reconcile to code) vs **`terraform import` / state surgery** (reconcile code to reality). State surgery is a last resort; document why in the commit.
- Never run destructive Terraform (`destroy`, target-destroy, state-rm) without explicit user confirmation, even with `--auto`.
- K8s: prefer fixing the manifest / Helm values, not `kubectl edit` on the cluster. If you must hotfix live, mirror the change back to the manifest in the same PR.
- CI/CD: pin the broken thing (action SHA, dependency version) only if the upstream regression is confirmed. Otherwise fix the workflow.
- Secrets: rotate, don't paste. If a secret leaked into a log or commit, rotation is part of the fix.

## Diff hygiene

- Group related edits in a single commit; keep unrelated changes out.
- No commented-out code, no `// removed` / `// old` markers — git history is the record.
- No new TODOs about the fix itself. TODOs about adjacent issues are fine but rare.
- No backwards-compat shims unless the spec explicitly requires them.

## When mid-fix you discover the diagnosis was wrong

Stop. Don't keep editing. Go back to Step 2 with the new evidence. Two wrong diagnoses in a row → re-scout (the boundary you thought was relevant probably isn't).
