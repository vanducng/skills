---
name: agent-readiness
description: "Scores how ready a repository is for AI coding agents to work in it effectively, then remediates the gaps - grades agent instruction files, verifiable feedback loops, onboarding reproducibility, and codebase navigability against a fixed 30-signal rubric, stack-agnostic across TypeScript, Python, Go, Rust, Ruby, Java, C#, and PHP/Laravel. Activates when the user says 'is this repo agent-ready', 'readiness report', 'readiness score', 'agent readiness', 'audit this repo for AI agents', 'why do agents struggle in this codebase', 'make this repo agent-friendly', 'audit our agent instruction files', or 'score our agent readiness'. Owns the scoring and the remediation plan; defers the writing of ./docs content to vd:docs, locating code to vd:scout, public documentation sites to vd:docs site, refactoring a change toward its intended architecture to vd:simplify --aggressive, and authoring instruction files and skills to vd:skill-creator."
license: MIT
argument-hint: "[path] [--report | --fix] [--group <1-4|name>]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Agent Readiness

> An agent's effectiveness in a repo is capped by what the repo lets it verify. Score the affordances, not the code quality.

## What this skill is - and isn't

| Skill | Question it answers | Output |
|---|---|---|
| **`vd:agent-readiness`** (this) | "How well can an AI agent work in this repo, and what is missing?" | A scored report; optionally safe additive fixes plus a proposal list |
| `vd:docs` | "Are the shared `./docs/` files true and current?" (`site` subcommand: "How do we publish a public docs site?") | Written docs content / a Starlight site |
| `vd:scout` | "Where does X live in this repo?" | A file map, no writes |
| `vd:simplify --aggressive` | "What would this change look like if the architecture existed from day one?" | A refactored diff |
| `vd:skill-creator` | "How do I author a skill an agent reliably loads?" | A `SKILL.md` |

This skill **measures and remediates affordances**. It may create a scaffold (an `AGENTS.md`, an
`ARCHITECTURE.md`) only when the repo's own evidence fills it enough to pass the signal, then hands the prose
to the owning skill. It never writes the architecture narrative, and never refactors code to raise a score.

## Hard rules

1. **Identical repo, identical output.** Score on committed evidence. Prefer existence checks over deep semantic analysis, order signals by id, and cap each rationale at ~500 characters. Record an `as_of` date and score every date-relative clause against it, run runnable checks in the repo's declared environment rather than against whatever the host happens to have installed, and treat missing API access as a fallback to static config evidence - never as non-applicability. Live measurements (CI durations, status APIs) are reported as observations and never change a score. A score that drifts with the host, the clock, or a token's permissions is not a property of the repo. **One signal is explicitly weaker:** `service_dependencies_documented` matches config keys to services by name, so `references/signals.md` marks it `determinism: narrowed` and requires the collected list verbatim in the rationale. That caveat is named rather than hidden; no other signal may claim it.
2. **If evidence is ambiguous, fail the item.** A plausible filename is not a passing check. Optimistic scoring produces a number the user cannot act on.
3. **Every signal is evaluated on every repo.** Stack detection selects which evidence to look for; it never changes which signals are scored. Only signals explicitly marked skippable in the `references/signals.md` registry may score `null`. **A missing or unreadable `references/stacks/<name>.md` is never a skip:** score that stack's signals on each signal's language-agnostic catch-all clause and record the gap in the report. Dropping them shrinks `n` and inflates the pass rate, hiding the finding instead of reporting it.
4. **A fix that breaks existing tests is evidence the fix is wrong, not that the tests are wrong.** Proven the hard way: a readiness pass added a hard-throwing N+1 query guard, 21 tests broke, and the correct resolution was switching the guard to detect-and-log. Never adjust, skip, or delete a test to make a readiness fix pass.
5. **Never game a signal.** No empty placeholder files, no config that technically satisfies a check while providing no value, no disabling a check so it stops failing. A signal exists to make the repo better for an agent, not to raise a number.
6. **Re-score after fixing, never project.** Re-run the full scan **per branch** and report that branch's real before and after. There is no combined after-score across group branches, and an unapplied proposal moves no score - it is reported as pending and unverified. An arithmetic projection ("53.9% should reach ~66%") is unverified and has been wrong.
7. **Auto-apply only what passes the four-part safe test** in `## --fix mode`. Everything else is a proposal the user approves. The per-signal `Fix:` line in `references/signals.md` is the only classification list; there is no second summary to consult.
8. **Isolate the change, one signal group at a time.** Never commit readiness fixes to the mainline. The default is one group per branch and per PR, so a rejected fix cannot block the accepted ones; `references/signals.md` § Branching and re-scoring defines the dirty-tree, existing-branch, no-remote, and trunk-based fallbacks.

## Workflow

### 1. Scope the repository

Resolve the target path (default: the current repo root) and run `references/signals.md` § Preflight, which
gives a defined score-or-skip outcome for a non-git target, no CI config, unrunnable tooling, and a read-only
sandbox. Record `as_of` (the UTC scan date) in the report header.

Discover apps per `references/signals.md` § App discovery: collect candidates from concrete markers
(workspace members, `go.mod`, Cargo members, `pom.xml` modules, `composer.json`, `pyproject.toml`, a
`Dockerfile`, a deployment marker **carrying an explicit source mapping**), subtract the named exclusion paths,
and dedupe to the outermost manifest. An image-only deployment manifest maps to no source directory, so it is
context and not an app. "Could it move to its own repo?" is a tiebreaker only. If 0 candidates survive, count
the repo root as 1. Detect the stack per app per § Stack detection, which is also the index naming each stack's
`references/stacks/<name>.md`; an app may match several, and a signal then passes for that app only when **every
code-bearing stack** in it passes. Record the per-stack verdict so a partial pass stays visible.

**Verify:** print `as_of`, the app list, and the detected stacks before scoring. A wrong N distorts every
app-scope signal, and the user is the cheapest place to catch it.

### 2. Score the signals

Load the signal registry in `references/signals.md` - all 30 ids (7 / 9 / 7 / 7) with scope, skippability, fix
class, and where the evidence lives - then load `references/stacks/<name>.md` for every stack detected in step 1.
The registry defines the denominator; the stack files supply per-language evidence for the 13 stack-heavy signals.
Walk all 30 in id order, recording `id`, group, scope, `numerator/denominator`, the deciding evidence, and a
rationale under ~500 characters. A skipped signal records `null` plus its reason - only its own stated skip
condition qualifies, never an unreachable API, an uninstalled tool, or a missing stack file.

**Verify:** every signal has a score and a named piece of evidence. A verdict with no evidence is a guess -
re-inspect or fail it.

### 3. Report

Follow the canonical template in `references/signals.md` § Report contract: the filename fallback when no Reports
path is injected, one-decimal percentages, the table columns, the sort keys (signals in id order; gaps by group
then id), and any stack that had no file (rule 3). Ranking is **remediation priority, not scoring weight** - all
signals score equally, but fix Group 2 gaps first: they remove the agent's ability to self-check.

**Verify:** recompute the pass rate from the signal table and confirm it matches the headline number.

### 4. Fix (only with `--fix`)

See `## --fix mode`, then return to step 2 and re-score that branch.

## Scoring

Each signal scores a ratio `numerator/denominator`:

| Scope | Denominator | Numerator |
|---|---|---|
| repo | 1 | 1 if it passes, 0 if not |
| app | N = apps discovered | how many apps pass |
| skipped (skippable only) | excluded | `null` |

```
pass_rate_pct = 100 * sum(numerator_i / denominator_i) / n    where n = count of non-skipped signals
```

The result is a **percentage in [0, 100]**, rounded half up to **one decimal place** (`53.85` renders
`53.9`) before comparison to a band, so two agents computing the same ratio report the same number and land
in the same band at a boundary. A repo passing every signal scores `100 * n/n = 100.0%` (Level 5); one
passing none scores `0.0%` (Level 1). **All signals are weighted equally**, and skipped signals leave the
denominator entirely, so a repo is never penalised for a signal that does not apply to it.

Bands are half-open, so every pass rate lands in exactly one: `[a, b)` includes `a` and excludes `b`. There
is no Level 6. Report the raw percentage alongside the level so progress within a band stays visible.

| Pass rate (%) | Level | Reading |
|---|---|---|
| `[0, 20)` | Level 1 | An agent works blind; every task needs a human in the loop |
| `[20, 40)` | Level 2 | Basic affordances exist but are unreliable or undocumented |
| `[40, 60)` | Level 3 | An agent can build and test, but cannot navigate or self-verify fully |
| `[60, 80)` | Level 4 | An agent works productively; gaps are specific and known |
| `[80, 100]` | Level 5 | An agent can pick up a task, verify it, and ship it unaided |

## `--fix` mode

**Auto-applyable (safe).** All four must hold:

1. It creates a **new** file rather than editing an existing one.
2. Any check it introduces is **advisory** - lint rules at `warn` severity, CI steps with `continue-on-error: true` - so it cannot fail a build on pre-existing code. Before applying, grep the repo for warning-to-error policies (`--max-warnings=0`, `-Werror`, `-D warnings`, `TreatWarningsAsErrors`, `failOnWarning`, `strict = true` on the linter). Under any of them a `warn` rule is a build failure and the fix is not advisory.
3. It changes **no runtime behaviour**.
4. **No build, CI, dependency, or runtime tool acts on the new file.** It fails this condition when an existing local or remote **tool** discovers it by path and then *does something*: executes code, gates a merge, requests reviewers, opens PRs, switches an interpreter, or joins a run. `CODEOWNERS` requests reviewers, a `dependabot.yml` opens scheduled PRs, a `.github/workflows/*.yml` runs on the next push, a `.nvmrc`/`.python-version`/`.tool-versions` switches the interpreter for everyone, and a linter config at a discovered path joins the next lint run.

**Read-only-document carve-out.** A file that only a human or an agent *reads* passes condition 4 even
though it is auto-discovered: instruction files (`AGENTS.md`, `CLAUDE.md`), PR and issue templates, docs
stubs. Nothing executes them, nothing gates on them, no build changes. An instruction file does change
future *agent* behaviour - that is the fix's entire intent, not a side effect to guard against - and the
stub rule below keeps it honest: evidence-filled, never hollow.

Qualifying categories, all four checked: a dead-code or duplicate-code tool config plus a standalone runner
script nothing yet calls, a marker scanner script, and the read-only documents above. Categories failing
condition 4: CI workflow files, review and dependency automation config, runtime-version selectors. Every
per-signal classification lives on the `Fix:` line in `references/signals.md` (rule 7), never a list here.

**Stub rule.** A generated stub may be auto-applied only when it already satisfies the signal it targets -
real resolved commands, real top-level directory names, over the 100-character floor. A hollow skeleton
(`# Architecture` + `TODO`) fails its own signal's content clause and violates rule 5, so it is
propose-only; hand the writing to `vd:docs` or `vd:skill-creator`.

**Propose only (never auto-apply).** Any one of these disqualifies a fix:

| Category | Why it is not safe |
|---|---|
| Editing or reformatting an existing file | Overwrites a maintainer decision; a tree-wide reformat buries the next diff |
| Changing runtime behaviour | A readiness score is not worth a production incident |
| Gating CI or blocking merges | Turns a pre-existing gap into a broken build for everyone |
| Adding a dependency | Supply-chain and maintenance cost the user must weigh |
| Lowering or disabling an existing check | Reduces real safety to raise a number |
| A new file a build, CI, dependency, or runtime tool acts on | Takes effect on creation - condition 4. A file only a human or agent reads is carved out |
| A `warn`-severity rule in a repo that treats warnings as errors | The advisory rule is a build failure there |
| A stub the repo cannot fill from real evidence | Fails the signal it targets and games it - rule 5 |
| Repo metadata or remote changes (branch protection, labels, enabling scanning) | Outside the working tree; often irreversible without admin |

Present proposals as a concrete diff or a checklist the user approves item by item.

**After fixing:** run the repo's own commands (test, lint, build) in its declared environment, report
exactly what was run and the result, then re-score that branch per rule 6. When the commands cannot be run
(tooling absent or execution not permitted), say so and report which fixes are therefore unverified; never
claim a green run you did not observe.

## Anti-patterns

- **Running the full test suite to score `test_command_runnable`.** Slow, can mutate state, and conflates "the command works" with "the tests pass". Use a collection-only or dry-run flag.
- **Hardcoding one stack's evidence.** The original rubric checked `tsconfig.json` strict and `[tool.black]` with no fallback, so Go, Rust, and PHP repos matched no rule and the scoring improvised. Every criterion needs its per-language clauses (`references/stacks/`) plus a catch-all.
- **Auto-applying a formatter.** Passes `format_check_available` and rewrites blame for the whole tree.
- **Creating an `AGENTS.md` with a heading and a TODO.** Fails its own 100-character floor and teaches an agent nothing. A stub earns auto-apply only when generated content already passes the signal.
- **Treating "it is a new file" as "nothing acts on it".** `CODEOWNERS`, `dependabot.yml`, a workflow file, and `.nvmrc` all act the moment they land. Condition 4 exists because of this - and it is about tools acting, not about a document being read.
- **Scoring a signal on a live API result.** The same commit must score the same with a token and without one. CI durations and status checks are observations in the rationale, never score inputs.
- **Scoring against the host.** A missing binary is not a repo gap, and a token without API access is not a skippable signal.
- **Scoring app-scope signals against the root only.** Root-only instructions in a 6-app monorepo are 1/6, not 1/1. Collapsing that hides exactly the gap the user is asking about.
- **Reporting a projected score.** Only a re-run counts.
- **Rewriting the rubric mid-run.** Adjusting a criterion because the repo fails it turns the score into an opinion.

## Rationalizations to catch

| Thought | Reality |
|---|---|
| "This config is obviously safe to add" | It is safe only if it is new, advisory, non-runtime, and acted on by no tool. Check all four. |
| "It's a new file, so it can't break anything" | A path a build, CI, or runtime tool acts on takes effect on creation. Condition 4. |
| "An `AGENTS.md` is auto-discovered, so condition 4 blocks it" | Read-only-document carve-out. Nothing executes or gates on it; the stub rule is the guard. |
| "The suite is red but the commands all work" | `verification_baseline_green`. An agent there cannot tell its regression from the baseline. |
| "`warn` severity can't fail CI" | It does under `--max-warnings=0`, `-Werror`, or `TreatWarningsAsErrors`. Grep first. |
| "The API is unreachable, so this signal is null" | Only a signal's own skip condition nulls it. Fall back to static CI config. |
| "The tests were already fragile" | Rule 4. A fix that breaks tests is the wrong fix. |
| "An empty `.env.example` still passes the check" | Gaming the signal. It has to list the variables the code actually reads. |
| "This repo has no CI, so most signals should be skipped" | Only signals marked skippable may be null. Missing CI is a 0, and that is the finding. |
| "I can compute the new score from the fixes I made" | Rule 6. Projections have been wrong; re-run the scan. |
| "PHP/Go isn't in the rubric, so I'll approximate" | `references/stacks/` holds a file per stack, eight of them, plus a catch-all clause per criterion. Use it. |
| "There's no stack file for this language, so skip its signals" | Rule 3. Score them on the catch-all and report the gap; skipping inflates the rate. |
| "Branch protection would fix three signals at once" | A remote change. Propose it; never apply it. |

## Workflow position

```
"is this repo agent-ready?"
        ↓
vd:agent-readiness --report  →  scored report + ranked gaps
        ↓ (--fix)
branch per group → safe fixes applied → proposals for approval
        ↓
re-score per branch (real, not projected)  →  vd:code-review  →  vd:ship
        ↓
hand off writing: vd:docs (architecture, guidelines) · vd:skill-creator (skills/)
```
