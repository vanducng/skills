# Audit checklist - six categories

This file is the authoritative checklist the audit subagent walks. It is **pasted verbatim** into the subagent prompt - keep it self-contained, no external references the subagent can't follow.

## Severity definitions

| Severity | Meaning | Example |
|---|---|---|
| **CRITICAL** | Plan will FAIL at execution | Phase 3 calls a migration that has no rollback; phase order will deadlock; required dep is missing from any install step |
| **HIGH** | Plan will succeed but produce a flawed result | No tests planned for new business logic; success criteria are unverifiable; no rollback path for irreversible op |
| **MEDIUM** | Quality / maintenance issue | Vague success criteria ("works correctly"); naming convention drift; phase too coarse for one PR |
| **LOW** | Observational, no action required | Effort estimate seems generous; alternative pattern exists but current is fine; minor doc-style nit |

**Rule:** Do not inflate. A `MEDIUM` mis-classed as `HIGH` trains the author to ignore findings. A clean-feeling plan with one CRITICAL finding is more useful than a noisy plan with ten LOWs.

## 1. Cross-phase consistency

Walk all phases as a set. Look for:

- **File path conflicts** - phase 2 modifies `src/foo.ts` but phase 4 deletes it; phase 3 creates `src/bar.ts` and phase 5 also creates `src/bar.ts`
- **Phase ordering bugs** - phase 5 imports a symbol that phase 7 creates; phase 3 tests a feature added in phase 4
- **Library / framework conflicts** - phase 2 picks library X, phase 5 references library Y for the same job
- **Constraint contradictions** - `plan.md` says "no new deps" but phase 4 adds a dep; constraint says "Node 18+" but phase 6 uses a Node 20-only API
- **Status drift** - `plan.md`'s phases table doesn't match the actual phase frontmatter (e.g. table says phase 3 = "in-progress", phase file says "pending")
- **Naming drift** - phases use different verbs/nouns for the same thing across files

Severity rule of thumb: file conflicts → CRITICAL. Ordering bugs → CRITICAL. Library conflicts → HIGH. Status drift → MEDIUM.

## 2. Codebase reality (drift)

The plan was written against a snapshot of the codebase. Spot-check that the snapshot still matches:

- **Referenced files exist** - every path under `**Modify:**` and `**Delete:**` exists at the expected path
- **Referenced symbols / functions exist** - if a phase says "extend `parseConfig()` in `src/config.ts`", verify both the file and the function
- **Naming conventions match** - if existing files use `kebab-case` and the plan creates `PascalCase` files, flag it
- **Module structure matches** - plan says "add to `src/lib/`" but repo has no `src/lib/`; only `lib/`
- **Tooling assumptions** - plan says "run `pnpm test`" but repo uses `npm`; plan says "use `vitest`" but repo uses `jest`

Use Read/Glob/Grep on the codebase root (provided in prompt) to spot-check. Don't read more than ~20 files - sample, don't audit the whole repo.

Severity: missing files / wrong tools → CRITICAL. Naming drift → MEDIUM.

## 3. Missing scaffolding

Based on what the plan is shipping, infer what's needed but missing. Common gaps:

| Feature shape | Often-missing scaffolding |
|---|---|
| New API endpoint | Auth check; rate limit; input validation; error handling; observability (log/trace); OpenAPI/schema update |
| New database table / column | Migration; rollback; backfill (if NOT NULL on existing rows); index strategy; data-retention plan |
| New external integration | Secrets management; retry / backoff; circuit breaker; error-mapping back to user-facing language |
| New UI feature | Loading state; error state; empty state; a11y (labels, focus order); responsive breakpoints; i18n keys |
| New background job | Idempotency; retry policy; dead-letter handling; observability; how to disable it (kill switch / feature flag) |
| New deploy / infra change | IAM / permissions; rollback plan; staged rollout (canary); monitoring + alerts; cost impact |
| New shared library / utility | Tests; usage doc / examples; semver impact on consumers |
| Refactor with no behavior change | Tests proving behavior unchanged BEFORE refactor; perf comparison |

**Honor `decisions.md`.** If the user explicitly said "no auth - internal tool", do NOT flag missing auth.

Severity: missing migration / rollback for irreversible op → CRITICAL. Missing tests on new logic → HIGH. Missing observability → HIGH. Missing a11y / i18n → MEDIUM (unless plan explicitly serves multilingual / accessible audience → HIGH).

## 4. Unrealistic / unverifiable success criteria

Every success criterion should be a thing a human or test can observably check. Flag:

- **Vague phrasing** - "code works correctly", "feature is robust", "performance is acceptable"
- **No measurement infra** - "p95 latency < 100ms" but no instrumentation phase / no baseline capture
- **Missing baseline** - performance / quality criteria with no "before" number
- **Unmeasurable behavior** - "users find the UI intuitive" with no usability test or metric defined
- **Test criteria with no test runner mentioned** - "all unit tests pass" but no phase mentions setting up the test runner / no test files listed
- **Criteria the plan can't deliver** - "100% test coverage" but no testing phase

Severity: vague phrasing → MEDIUM. No baseline for perf → HIGH. Criteria the plan can't deliver → HIGH.

## 5. Dependency & sequencing gaps

Things the plan assumes are in place but never sets up:

- **External services / APIs** - phase 4 calls "the X API" but no phase obtains credentials / sets up env var
- **Env vars / config** - phase mentions `process.env.FOO` but no phase says where `FOO` is defined
- **Secrets** - phase needs a key but no phase covers secret storage / rotation
- **Tooling / CLI** - phase says "run `mise install`" but `mise` isn't documented as a prerequisite
- **Package install steps** - phase imports a library that no phase installs
- **Migration / fixture state** - phase assumes a DB row exists but no fixture / seed phase creates it
- **Branch / repo state** - phase assumes a feature flag is enabled / a config exists but doesn't set it

Severity: missing creds / env vars at execution time → CRITICAL. Missing install / setup → HIGH. Missing prereq doc → MEDIUM.

## 6. Scope drift / phase shape

Inspect each phase as a unit:

- **Too coarse** - "implement auth" with 15 steps spanning 6 files = unreviewable PR. Split.
- **Too granular** - "create file foo.ts" / "add export statement" / "add semicolon" as separate phases = wasted ceremony. Merge.
- **Phase shouldn't ship alone** - "add migration" is fine; "add half a migration" isn't. If a phase leaves the system broken, it's not a phase.
- **Hidden phases** - `Steps` section talks about "also add the matching frontend code" but no phase covers that.
- **Dependency leaks** - phase says `depends_on: []` but actually needs phase 2 to have shipped.
- **Effort estimate way off** - `effort: "1h"` for a phase touching 12 files; or `effort: "2d"` for a 1-line config change.

Severity: phase ships broken state → CRITICAL. Hidden phases / dep leaks → HIGH. Too coarse / too granular → MEDIUM. Effort off → LOW.

## Decisions.md handling (cross-cutting)

If `decisions.md` is provided in your inputs, it lists what the author intentionally excluded. Before emitting any finding, check:

1. Does this finding match a "Non-goals" entry? → DROP it. Don't emit.
2. Does this finding flag the unchosen side of a "Trade-offs" entry? → DROP it. Author already chose.
3. Does this finding contradict a "Constraints accepted" entry? → If acting on it would require violating the constraint, DROP. Otherwise emit at most as MEDIUM with note "constraint may need revisiting" - never CRITICAL/HIGH.

A finding suppressed by `decisions.md` should be mentioned in the report's "Decisions respected" section so the author can verify the audit honored their intent.

## Output reminder

The subagent must return JSON only - shape defined in the calling prompt. No prose preamble, no commentary. The controller renders the markdown report from the JSON.
