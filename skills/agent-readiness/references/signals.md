# Agent-readiness signal rubric

30 signals in 4 groups (7 / 9 / 7 / 7). Every signal is evaluated on every repository. **Stack detection
selects which evidence to look for; it never changes which signals are evaluated.** A Go repo and a
Laravel repo are scored against the same 30 rows, only the accepted evidence differs.

## Layout: this file and the stack files

The rubric is a signal x stack matrix. This file owns the **signal axis**: the registry of all 30, the
scoring rules, and the full definition of the 17 signals whose evidence is the same in every ecosystem.
`stacks/*.md` owns the **stack axis**: one file per ecosystem, each carrying a row for every one of the 13
stack-heavy signals. Adding a ninth language is one new file plus one registry line, not an edit spread
across thirteen definitions.

| Question | File |
|---|---|
| Which signals exist, how are they scored, is this one skippable, what is its fix class | this file |
| What counts as evidence for `lint_configured` in Rust | `stacks/rust.md`, row `lint_configured` |
| How do I add a ninth stack | `stacks/_template.md` |

A stack file never changes a signal's scope, skippability, or fix class, and never removes a signal's
catch-all clause. It only supplies the per-language clauses.

**A missing stack file is an error, never a skipped signal.** If a detected stack has no file under
`stacks/`, score that stack's 13 signals against each signal's language-agnostic catch-all clause and
**record the gap in the report** (the stack name and the signals scored that way). Never drop the signal:
skipping shrinks `n` and inflates the pass rate, which is the opposite of the finding. The same applies to
a stack file that is present but missing a row for a signal id.

## Signal registry (all 30)

The denominator depends on this table. Every signal id the run scores appears here exactly once, so `n` is
countable in one place, and any id present in a stack file but absent here (or the reverse) is a defect in
the rubric rather than a scoring judgement.

`Fix` repeats the signal's own `Fix:` line for orientation only. `safe if*` means the classification is
conditional and the signal's `Fix:` line states the condition; read that line before applying anything.

| id | Group | Scope | Skippable | Fix | Evidence |
|---|---|---|---|---|---|
| agent_instructions_present | 1 | repo | no | safe if* | this file |
| instructions_document_commands | 1 | repo | no | propose | this file |
| instructions_validated_in_ci | 1 | repo | no | propose | this file |
| instructions_freshness | 1 | repo | no | propose | this file |
| instructions_scoped_per_app | 1 | app | no | safe if* | this file |
| skills_or_prompt_library | 1 | repo | yes | propose | this file |
| agent_config_committed | 1 | repo | yes | propose | this file |
| test_command_declared | 2 | app | no | propose | stack file |
| test_command_runnable | 2 | app | no | propose | stack file |
| lint_configured | 2 | app | no | propose | stack file |
| format_check_available | 2 | app | no | propose | stack file |
| static_analysis_configured | 2 | app | no | propose | stack file |
| coverage_threshold_enforced | 2 | app | no | propose | stack file |
| ci_runs_on_pull_requests | 2 | repo | no | propose | this file |
| ci_feedback_fast | 2 | repo | yes | propose | this file |
| verification_baseline_green | 2 | app | no | propose | this file |
| single_command_setup | 3 | repo | no | propose | this file |
| env_vars_documented | 3 | repo | yes | safe if* | this file; env-access API per stack file |
| dependencies_locked | 3 | app | no | propose | stack file |
| runtime_version_pinned | 3 | app | no | propose | stack file |
| dev_environment_declared | 3 | repo | no | propose | this file |
| service_dependencies_documented | 3 | repo | yes | propose | this file; extractor keys per stack file |
| readme_setup_steps | 3 | repo | no | safe if* | this file |
| architecture_documented | 4 | repo | no | safe if* | this file |
| module_boundaries_enforced | 4 | repo | yes | propose | stack file |
| dead_code_detection | 4 | app | no | safe if* | stack file |
| duplicate_code_detection | 4 | repo | no | safe if* | stack file |
| file_size_or_complexity_guard | 4 | repo | no | propose | stack file |
| naming_conventions_stated | 4 | repo | no | propose | stack file |
| tech_debt_markers_tracked | 4 | repo | no | safe if* | this file; marker rules per stack file |

## How to read a signal

| Field | Meaning |
|---|---|
| `id` | snake_case, stable across runs, used in the report and in fix branch names |
| Scope | `repo` = scored once, denominator 1. `app` = scored per discovered app, denominator N |
| Skippable | `yes` = may score `null` and drop out of the final denominator. `no` = must score 0 or 1 |
| Inspect | the files/commands to look at. Existence checks first, semantics only when cheap |
| PASS if ANY ONE of | satisfying a single clause passes the signal. The last clause is always a language-agnostic catch-all |
| Stack evidence | for the 13 stack-heavy signals the per-language clauses live in `stacks/<name>.md` under the signal's own id; the catch-all stays here |
| Fix | **the single source of truth for fix classification.** `safe` = auto-applyable under the four-part test in SKILL.md `## --fix mode`. `safe if <condition>` = safe only while that condition holds, propose otherwise. `propose` = present as a diff, never write |

The registry's `Fix` column is an index, not a second classification: it never states a condition, and
`safe if*` always sends you back to the signal's own `Fix:` line. Read that line on the signal you are about
to fix and nothing else. Two lists that both claim to decide would drift, and then two agents mutate
different files.

Ambiguous evidence fails the item. Do not infer a passing state from a plausible-looking filename.

## Recording the run: `as_of`

Every report records `as_of`, the UTC date the scan ran, and every date-relative clause is evaluated
against `as_of` rather than "today". Two runs of the same commit with the same `as_of` must produce the
same score. When re-scoring after a fix (SKILL.md rule 6), reuse the first run's `as_of` so the delta
reflects the fix and not the calendar.

Runnable checks (`test_command_runnable`) run **inside the repo's own declared environment** - its
devcontainer, its compose service, its `mise`/`asdf`/`nvm` version file, its documented interpreter. A
tool missing from the host is not repo evidence: when the declared environment cannot be entered, score
on **declared-and-resolvable** evidence (the command resolves to a real script/target and its runner is a
resolved dependency in a committed manifest or lockfile) and say so in the rationale.

**Lack of API access is not non-applicability.** When a CI history or provider API is unreachable, fall
back to the static CI-config clauses of the signal and score them. A signal scores `null` only when it is
marked skippable AND its skip condition is genuinely met by the repo's contents.

## Preflight: unsupported targets

Run these four checks before scoring and print the outcome. Every case has a defined score-or-skip outcome,
because an undefined case is exactly where two agents diverge.

| Condition | Detect by | Outcome |
|---|---|---|
| Not a git repo | `git -C <path> rev-parse --git-dir` fails | Score everything else normally. `instructions_freshness` scores **0** (its evidence is a commit date that does not exist - ambiguous evidence fails the item, and it is not skippable). `ci_feedback_fast` is unaffected: it is scored on committed config, not history. State "no git history" in both rationales and in the report header. |
| No CI config committed | none of `.github/workflows/*`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/config.yml`, `azure-pipelines.yml`, `.buildkite/` | `ci_feedback_fast` scores `null` (its stated skip condition). `instructions_validated_in_ci`, `ci_runs_on_pull_requests`, `verification_baseline_green` score **0** - not skippable, and missing CI is the finding. |
| Tooling not installed, or running it is not permitted | the declared environment cannot be entered, or the host forbids execution | Use the declared-and-resolvable fallback above for every runnable check and say so in the rationale. Never `null`, never a warning-only outcome. |
| Read-only sandbox (fixes cannot be written) | the working tree is not writable, or `--fix` was requested without write permission | Score and report normally, then downgrade `--fix` to `--report`: emit every fix as a proposal diff, apply nothing, and state in the report that no fix was applied and therefore the after-score equals the before-score. |

An empty git repo needs no case of its own: App discovery finds 0 candidates and its root-as-one-app
fallback counts the root as 1 app.

## App discovery

Discovery is manifest and workspace driven. Walk the tree once and collect candidate directories from
these concrete markers:

| Marker | Yields |
|---|---|
| `package.json` `workspaces`, `pnpm-workspace.yaml`, `lerna.json`, `nx.json`, `turbo.json` | each resolved workspace member directory |
| `go.work` `use` entries, or any directory with its own `go.mod` | that directory |
| Cargo workspace `members` (root `Cargo.toml`), or a `Cargo.toml` with a `[[bin]]`/`src/main.rs` | that directory |
| `pom.xml` `<modules>`, Gradle `settings.gradle{,.kts}` `include` | each module directory |
| `composer.json`, `pyproject.toml`, `setup.py`, `Gemfile`, `*.csproj` | that directory |
| A `Dockerfile` | the directory containing it |
| A deployment marker (`k8s/`, `helm/`, `*.yaml` with `kind: Deployment`, `fly.toml`, `Procfile`, `serverless.yml`) **that carries an explicit source mapping** | the mapped source directory |

A deployment marker yields an app only through an explicit, committed source mapping: a compose/build
`context:` path, a `dockerfile:`/`--file` path, a Helm chart or manifest field naming a source directory, a
`fly.toml` `build.dockerfile`, a `Procfile` process command whose working directory or entrypoint script
path is in the repo, or a `serverless.yml` handler path. **A deployment manifest with no such mapping (an
image-only `kind: Deployment` referencing `ghcr.io/org/api:1.4.0`, a chart with only `image.repository`) is
excluded from app discovery entirely.** Do not count the manifest's own directory, do not count the repo
root on its behalf, and never guess the service directory from the image name - all three choices change N
and therefore every app-scope score. Such a manifest is context: report it under
`service_dependencies_documented` and `dev_environment_declared` evidence, not as an app.

Then subtract the exclusions - a candidate is **not** an app when its path contains any of:
`examples/`, `example/`, `demos/`, `demo/`, `docs/`, `test/`, `tests/`, `testdata/`, `fixtures/`,
`__mocks__/`, `vendor/`, `node_modules/`, `third_party/`, `.venv/`, `target/`, `dist/`, `build/`,
`generated/`, `.git/`.

Deduplicate nested candidates to the outermost directory that has its own manifest. If 0 candidates
survive, count the repo root as 1 app. Record the final list in the report: a wrong N silently distorts
every app-scope signal.

*Could this directory be moved to its own repository and still function?* is a **tiebreaker only**, used
when two markers disagree about the boundary (for example a `Dockerfile` one level above a manifest). It
is never the primary test - it needs judgement, and judgement drifts between runs.

## Stack detection

This is also the **stack index**: the last column names the file holding that stack's evidence rows. A new
stack is added by creating its file from `stacks/_template.md` and adding a row here.

| Stack | Detect by | Manifest | Evidence file |
|---|---|---|---|
| TS/JS | `package.json` | `package.json`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `bun.lock` (or legacy `bun.lockb`) | `stacks/typescript-javascript.md` |
| Python | `pyproject.toml`, `setup.py`, `requirements*.txt` | `pyproject.toml`, `poetry.lock`, `uv.lock`, `Pipfile.lock` | `stacks/python.md` |
| Go | `go.mod` | `go.mod`, `go.sum` | `stacks/go.md` |
| Rust | `Cargo.toml` | `Cargo.toml`, `Cargo.lock` | `stacks/rust.md` |
| Ruby | `Gemfile` | `Gemfile`, `Gemfile.lock` | `stacks/ruby.md` |
| Java/Kotlin | `pom.xml`, `build.gradle{,.kts}` | same, plus `gradle.lockfile` | `stacks/java-kotlin.md` |
| C# | `*.csproj`, `*.sln` | `*.csproj`, `packages.lock.json` | `stacks/csharp-dotnet.md` |
| PHP/Laravel | `composer.json` | `composer.json`, `composer.lock` | `stacks/php-laravel.md` |

A stack detected here with no readable file in the last column falls back to the catch-all clauses and is
reported as a gap, per § Layout. It is never skipped.

**Multi-stack rule (deterministic).** An app may detect as several stacks. A signal passes for that app
only when **every code-bearing stack** in that app satisfies it. Evidence from a sibling app's stack never
counts. Concretely, for a stack-heavy signal: open each code-bearing stack's file, read the row for that
signal id, and pass the app only when every one of those rows is satisfied.

A detected stack is **code-bearing** for an app when both hold, checked against the app directory only
(exclusion paths from § App discovery removed):

1. It has its own manifest at or under the app directory (the Manifest column of the table above).
2. It has at least one first-party source file in that stack's languages under the app directory.

A stack that fails either test is not code-bearing and does not participate: a lone `.prettierrc` with no
`package.json`, a `package.json` that exists only to run a build tool with no `.ts`/`.js` source of its
own, or a `pyproject.toml` holding only tool config for a non-Python app. Record the code-bearing stack
list once per app; it is fixed for the whole run.

An app detecting PHP and TS, both code-bearing, passes `lint_configured` only with a `pint.json` (the
`lint_configured` row in `stacks/php-laravel.md`) **and** an `eslint.config.js` (the same row in
`stacks/typescript-javascript.md`). A `pint.json` alone scores that app 0 for the signal, because the TS half of the app
has no lint feedback loop and an agent editing it cannot check its own work. Record the per-stack verdict
in the rationale (`php=pass (pint.json), ts=fail (no eslint/biome config)`) so a partial pass stays visible
instead of being hidden behind a single 0.

ALL is as deterministic as ANY - both are fixed predicates over committed files - and it is the calibrated
one: a signal is meant to answer "can an agent verify its work here", and half an app is not the app.

---

## Group 1: Agent instruction files (7 signals)

Presence is cheap and near-universal; quality is what agents actually consume. Every signal here asks
whether the file would change an agent's behaviour, not whether it exists.

**`agent_instructions_present`** - repo scope, not skippable.
Fix: safe if the stub is generated from evidence that already satisfies the clause below (real resolved
commands and real top-level directory names, over 100 characters); propose otherwise. An instruction file
is read-only to every tool, so SKILL.md condition 4's carve-out applies and does not block it. A hollow
skeleton is still never safe - it fails this signal's own floor and breaks SKILL.md rule 5.
Inspect: repo root and `.github/`.
PASS if ANY ONE of:
- `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.cursor/rules/*.md`, `.windsurfrules`, or `.github/copilot-instructions.md` exists AND is longer than 100 characters of non-whitespace content.
- One of the above exists and imports another file (`@AGENTS.md`) whose combined content clears 100 characters.
- Any file the repo's own README names as the agent instruction entrypoint clears 100 characters.

A file under 100 characters fails: a title and a TODO teaches an agent nothing.

**`instructions_document_commands`** - repo scope, not skippable. Fix: propose (edits an existing file).
Inspect: the instruction file, then the manifest/task runner it points at.
PASS if ANY ONE of:
- The instruction file names **at least one command from each of build, test, and lint/format**, and each named command **resolves**: a `package.json` script, a `Makefile`/`justfile`/`Taskfile.yml` target, a `composer.json` script, a `pyproject.toml` tool entry, or an executable on the documented path.
- The stack has no build step (a library, a script package, an interpreted app with no bundler or compiler config) and it names at least one resolving command from each of test and lint/format.
- Any language: it links a `CONTRIBUTING.md` section naming those commands, and each resolves.

Count named-and-resolving commands per category; do not judge whether the set is complete. Fail if any
documented command does not resolve. A stale command is worse than none: the agent runs it, gets an error,
and starts improvising.

**`instructions_validated_in_ci`** - repo scope, not skippable. Fix: propose - the fix is a CI workflow
file, which executes on the next push (SKILL.md safe-test condition 4).
Inspect: `.github/workflows/*`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/config.yml`, pre-commit config.
PASS if ANY ONE of:
- A CI job runs a named script whose path exists and which reads the instruction file (existence, link resolution, command resolution, or a docs-sync check).
- A `.pre-commit-config.yaml` or `lefthook.yml`/`husky` hook invokes such a script.
- A CI job exits non-zero when the documented commands drift from the manifest (for example a generated-instructions diff check).

**`instructions_freshness`** - repo scope, not skippable. Fix: propose.
Inspect: `git log -1 --format=%cs -- <instruction file>` and `git log -1 --format=%cs`.
PASS if:
- The last commit touching the instruction file is within 180 days of `as_of`, OR the repo's own last commit is also more than 180 days before `as_of` (a dormant repo is not stale relative to itself).

Both dates come from git and are compared to the recorded `as_of`, never to the wall clock, so the same
commit scored with the same `as_of` always lands the same way.

**`instructions_scoped_per_app`** - app scope, not skippable.
Fix: safe if the app directory has no instruction file yet AND the per-app stub is generated from that
app's own resolved commands and directory names (over 100 characters); propose otherwise.
Inspect: each discovered app directory.
PASS per app if ANY ONE of:
- The app directory contains its own `AGENTS.md`/`CLAUDE.md` longer than 100 characters.
- The root instruction file contains the app's directory path verbatim AND, within the same section, either one resolving command for that app or a non-empty descriptive line about it.
- Single-app repo (N = 1, app is the repo root): the root instruction file passes `agent_instructions_present`.

Root-only instructions in a 6-app monorepo score 1/6, not 1/1. That ratio is the point: an agent dropped
into `services/billing` has no local map.

**`skills_or_prompt_library`** - repo scope, **skippable**. Fix: propose - a stub `SKILL.md` cannot be
filled from repo evidence (its value is authored judgement about when to load it), so it fails the stub rule
and SKILL.md rule 5. Hand it to `vd:skill-creator`. Condition 4 is not the reason: an agent loader only
reads it.
Skip when the repo declares no skill/prompt library and none of the paths below exist. Do not skip merely
because the library is small.
PASS if ANY ONE of:
- `skills/`, `.claude/skills/`, or `.agents/skills/` exists AND contains **at least one** `SKILL.md`, AND every `SKILL.md` in it has parseable frontmatter with a non-empty `name` and `description`.
- `.github/prompts/` or a documented prompt directory exists with at least one prompt file and a README explaining when to use each.

The at-least-one clause is not decoration: without it an empty `skills/` directory passes by vacuous truth
and earns a point for a library that contains nothing. One malformed `SKILL.md` fails the signal - most
loaders silently drop the whole skill.

**`agent_config_committed`** - repo scope, **skippable**. Fix: propose (permissions change behaviour).
Skip when the repo uses no agent tooling config.
PASS if ANY ONE of:
- `.claude/settings.json`, `.mcp.json`, `.cursor/mcp.json`, or an equivalent agent/MCP config is committed (not only in a gitignored local variant).
- `.github/copilot-instructions.md` plus a committed workflow that consumes it.
- An agent config is intentionally excluded and the instruction file says so and why.

---

## Group 2: Verifiable feedback loops (9 signals)

An agent cannot self-correct without a command that returns pass or fail. This group is the highest-value
group in practice: a repo scoring 0 here forces every verification back onto the human. Every fix in this
group is propose-only - each one either edits an existing config, gates CI, or adds a dependency.

**`test_command_declared`** - app scope, not skippable. Fix: propose.
Stack evidence: the `test_command_declared` row in each code-bearing stack's `stacks/*.md`.
PASS per app if ANY ONE of:
- Every code-bearing stack satisfies its own `test_command_declared` row.
- Any language: a `Makefile`/`justfile`/`Taskfile.yml` target named `test`, or a CI step that runs a test command.

**`test_command_runnable`** - app scope, not skippable. Fix: propose.
Verify with a **collection-only or dry-run** invocation, never the full suite, inside the repo's declared
environment. The invocation per runner is the `test_command_runnable` row in the stack file; for a task
runner use `just --dry-run test` or `make -n test`.

Pick the invocation for the runner the manifest actually declares. `--listTests` is Jest-only; `npm test`
does not accept it generically, and `dotnet build` compiles without discovering any test.
PASS per app if:
- The collection invocation exits 0 and reports at least one test, OR the runner exits 0 with a clean collection and the app has test files.
- Declared-and-resolvable fallback (declared environment unavailable): the test command resolves to a real script/target AND its runner is a resolved dependency in a committed manifest or lockfile. Record that the fallback was used.

Fail on a collection error, or on a required service the setup docs never mention. A binary missing from
the host is not a repo defect - use the fallback clause instead. Running the full suite is out of scope:
it is slow, it can mutate state, and a failing test is a different problem from an unrunnable command.

**`lint_configured`** - app scope, not skippable. Fix: propose. A new linter config is auto-discovered by
any linter the repo already runs, so it is not inert (SKILL.md condition 4), and under a
`--max-warnings=0`-style policy even a `warn` rule fails the build.
Stack evidence: the `lint_configured` row in each code-bearing stack's `stacks/*.md`.
PASS per app if ANY ONE of:
- Every code-bearing stack satisfies its own `lint_configured` row.
- Any language: a committed config file for a named linter that a CI job or documented command actually invokes.

**`format_check_available`** - app scope, not skippable. Fix: propose (the check step edits CI or the
manifest; a reformat rewrites the tree).
Config presence alone does not pass. Require **both** a resolved formatter (a dependency in the committed
manifest/lockfile, or a committed toolchain that provides it) **and** a declared non-mutating check
command.
Stack evidence: the `format_check_available` row in each code-bearing stack's `stacks/*.md`.
PASS per app if ANY ONE of:
- Every code-bearing stack satisfies its own `format_check_available` row.
- Any language: a declared command that reports formatting drift without rewriting files, whose tool resolves.

Never auto-apply a whole-tree reformat. It buries the next diff and rewrites blame for every file.

**`static_analysis_configured`** - app scope, not skippable. Fix: propose.
Require a resolved analyzer plus a declared invocation; a signature or type-stub directory is data, not an
analysis run.
Stack evidence: the `static_analysis_configured` row in each code-bearing stack's `stacks/*.md`.
PASS per app if ANY ONE of:
- Every code-bearing stack satisfies its own `static_analysis_configured` row.
- Any language: a committed static-analysis config that a CI job or documented command invokes.

**`coverage_threshold_enforced`** - app scope, not skippable. Fix: propose (a threshold gates CI).
Measurement alone does not pass; the threshold must be able to fail something.
**The floor must be meaningful.** A committed `0`, or a number at or below 1 percent, fails this signal: it
can never fail a build, so it gives an agent no signal about whether its change was tested. Accept either a
positive floor of **10 percent or more** (a fixed number chosen once, not per-run judgement), or a
**ratchet** - committed evidence that coverage cannot drop below the current measured baseline (a stored
baseline file the check compares against, a `--fail-under` value generated from the previous run, a service
config with "coverage must not decrease" on the diff). A ratchet passes at any absolute level, because it
still fails a build when the agent's change lowers coverage.
Stack evidence: the `coverage_threshold_enforced` row in each code-bearing stack's `stacks/*.md`.
PASS per app if ANY ONE of (each subject to the floor rule above):
- Every code-bearing stack satisfies its own `coverage_threshold_enforced` row.
- Any language: a CI step that exits non-zero when coverage drops below a committed number.

**`ci_runs_on_pull_requests`** - repo scope, not skippable. Fix: propose (CI gating).
PASS if ANY ONE of:
- A GitHub Actions workflow has a `pull_request` (or `merge_group`) trigger and runs at least one test or lint job.
- `.gitlab-ci.yml` has a merge-request rule, or Jenkins/CircleCI/Buildkite/Azure config runs on PRs.
- A committed pre-merge policy file (for example a required-checks config) plus the workflow it names.

**`ci_feedback_fast`** - repo scope, **skippable**. Fix: propose.
Skip **only** when the repo commits no CI config at all. No API access is not a skip.
**Scored on committed repository evidence only.** Live run history never changes the score, in either
direction: the same commit must score the same with a full-permission token, a read-only token, and no
token at all.
PASS if ANY ONE of:
- Every PR-triggered job declares a `timeout-minutes` (or the provider's equivalent: GitLab `timeout`, CircleCI `no_output_timeout` plus a job timeout, Buildkite `timeout_in_minutes`) of 15 or less.
- A documented fast-feedback split exists (a quick job gating merges, a slow job running post-merge), named in the CI config or in a committed doc that the config's job names match.
- The PR-triggered work is committed as parallel or sharded (a `strategy.matrix` splitting the suite, a `--shard`/`--split` flag, `parallelism: N`) **and** dependency caching is configured on those jobs (`actions/cache`, `cache:` in setup actions, GitLab `cache:`), so a cold serial run is not the steady state.
- A committed doc states a target feedback time of 15 minutes or less for PR checks and names the job it applies to.

An hour-long loop makes an agent guess instead of verify. When run history happens to be reachable, report
the observed median duration as an **observation** in the rationale, labelled as non-scoring context, and
still state which committed clause decided the score.

**`verification_baseline_green`** - app scope, not skippable. Fix: propose - every passing clause is a CI
gate, a branch-protection setting, or a claim about the suite this skill has not run.
A declared verification command is only useful if its **expected** result on a clean checkout is pass. In a
repo with a permanently red suite an agent cannot separate the regression it just caused from the baseline
it inherited, so every other signal in this group buys nothing.
**Scored on committed repository evidence only.** A live status API result is an observation, never a score
input, and this signal never runs the suite (SKILL.md anti-patterns).
PASS per app if ANY ONE of:
- The app's test job is a required status check: a committed branch-protection or merge-queue policy file (a rulesets export, `.github/settings.yml`, a Gitlab `merge_request` approval rule) names it, so the default branch cannot go red through the gate.
- The default branch's CI config runs that test job on `push` to the default branch (not only on `pull_request`) with no `continue-on-error` and no `|| true` in the step, so a red baseline is visible rather than tolerated.
- A README/CI badge is bound to the default branch (`?branch=<default>` or a workflow badge whose default is the default branch) for a workflow that runs the app's tests.
- A committed doc states the baseline explicitly: the verification command plus its expected clean-checkout result, dated or version-referenced, and every command it names resolves.
- The declared test job exists and the repo commits an allow-list of known-failing tests that the runner honours (a `--ignore`/`skip` list, an xfail set, a `.skip` manifest), so "green" is a defined state rather than a guess.

Fail when the test job is advisory everywhere it runs (`continue-on-error: true`, a trailing `|| true`,
`--exit-zero`), when it runs only on PRs from forks, or when the only evidence is an undated "tests should
pass" line with no resolving command. A suppressed exit code is the same as no baseline: nothing tells the
agent what green looks like.

---

## Group 3: Onboarding and environment reproducibility (7 signals)

An agent's first act in a repo is bringing it up. Every unstated step becomes a guess.

**`single_command_setup`** - repo scope, not skippable. Fix: propose. A setup script this skill has not
executed end to end is unverified, and executing setup mutates the machine.
PASS if ANY ONE of:
- A committed setup entrypoint (`bin/setup`, `setup.sh`, a `setup` target in `Makefile`/`justfile`/`Taskfile.yml`) whose body does **both**: installs dependencies via the app's package manager, and prepares local config (copies an example env file, generates a key, or migrates/seeds a local store).
- A compose file declares a service that builds or runs the app plus every service dependency it needs, and the README names `docker compose up` (or the equivalent) as the only command before the app is reachable.
- A devcontainer whose `postCreateCommand` runs that same dependency-install plus config-prepare pair.
- Any language: the README's setup section contains exactly one command line between clone and a runnable app.

Two commands is not one. `npm install && npm run db:migrate && cp .env.example .env` fails: each step is
a place to get stuck.

**`env_vars_documented`** - repo scope, **skippable**.
Fix: safe when creating a new `.env.example` whose keys are the variable names collected below, with empty
values; propose when an example file already exists (it would be edited) or when values must be guessed.
Skip only when the collection below yields zero variables.
Collect the variable names the code reads through its env-access API - the API per stack is the
`env_vars_documented` row in that stack's `stacks/*.md` - excluding matches under the discovery
exclusion paths (tests, fixtures, vendored and generated directories). For a stack with no file, collect
through whatever env-access API that language provides and note it in the rationale.
PASS if ANY ONE of:
- `.env.example`/`.env.sample`/`.env.dist` is committed and the collected set minus the keys it lists is empty, with **no real secret values**.
- A typed/validated config schema (a zod env schema, pydantic settings, `config/*.php` reading those keys) enumerates the collected set with nothing left over.
- The README or setup doc lists every name in the collected set with its purpose and whether it is required.

The predicate is a set difference over names, not a judgement about documentation quality. A committed
`.env.example` containing a live credential fails this signal and is reported as a security finding, not a
readiness gap.

**`dependencies_locked`** - app scope, not skippable. Fix: propose (generating a lockfile changes resolution).
Stack evidence: the `dependencies_locked` row in each code-bearing stack's `stacks/*.md`.
PASS per app if ANY ONE of:
- Every code-bearing stack satisfies its own `dependencies_locked` row.
- Any language: a committed lockfile or fully pinned manifest that reproduces an identical dependency set.

Check `.gitignore` too: an ignored lockfile fails even when the file exists locally.

**`runtime_version_pinned`** - app scope, not skippable. Fix: propose. A version-manager file is
auto-discovered: dropping `.nvmrc` or `.python-version` into a repo switches the interpreter for every
shell and hook that reads it (SKILL.md condition 4).
Accept only evidence that actually **controls** which runtime executes. Stack evidence: the
`runtime_version_pinned` row in each code-bearing stack's `stacks/*.md` names that ecosystem's accepted
files and its rejected compatibility declaration.
PASS per app if ANY ONE of:
- Every code-bearing stack satisfies its own `runtime_version_pinned` row.
- A version-manager file: `.nvmrc`, `.node-version`, `.python-version`, `.ruby-version`, `.tool-versions`, `mise.toml`, `rust-toolchain.toml`.
- An immutable container or devcontainer image reference: a digest (`@sha256:...`) or an exact version tag (`python:3.12.6-slim`); `:latest` or a floating major fails.
- An ecosystem SDK selector that pins: .NET `global.json`.

Compatibility declarations do **not** pass, because they express a minimum or a range rather than a
selection: npm `engines.node` (documented as advisory), `requires-python`, the `go` directive, Rust
`rust-version`, `<TargetFramework>`, and Composer's `require.php`. Composer's `config.platform` only
emulates a platform during resolution and does not choose the PHP that runs.

**`dev_environment_declared`** - repo scope, not skippable. Fix: propose (a container spec is runtime).
PASS if ANY ONE of:
- A `Dockerfile` plus a `compose.yaml`/`docker-compose.yml` that declares a service building or running this app, and a committed doc naming the command that starts it.
- `.devcontainer/devcontainer.json`.
- `flake.nix`/`shell.nix`, `mise.toml`, `.tool-versions`, `Vagrantfile`, or `Procfile` plus a committed doc naming the process manager it needs.
- Any language: a committed, executable declaration of the dev runtime that names every tool it provides and depends on no undocumented host state.

**`service_dependencies_documented`** - repo scope, **skippable**. Fix: propose.
Collect the service list mechanically: compose service names, plus config/env keys matching the fixed
prefix-or-suffix set `*_URL`, `*_DSN`, `*_HOST`, `DATABASE_*`, `REDIS_*`, `QUEUE_*`, `CACHE_*`, `MAIL_*`,
`S3_*`, `*_API_KEY`, `*_BASE_URL`, plus the driver values at the enumerated framework keys below.

**Driver extractors (the finite list - no other key contributes a service).** Read the literal or default
value at each path; a value read from an env var contributes that env var's name instead:

| Framework | Keys read |
|---|---|
| Laravel | `config/database.php` `connections.*.driver` and `redis.*` client, `config/queue.php` `connections.*.driver`, `config/cache.php` `stores.*.driver`, `config/mail.php` `mailers.*.transport`, `config/filesystems.php` `disks.*.driver`, `config/session.php` `driver` |
| Django | `settings*.py` `DATABASES[*]['ENGINE']`, `CACHES[*]['BACKEND']`, `EMAIL_BACKEND`, `CELERY_BROKER_URL`, `STORAGES`/`DEFAULT_FILE_STORAGE` |
| Spring | `application.{yml,yaml,properties}` `spring.datasource.*`, `spring.data.redis.*`, `spring.rabbitmq.*`, `spring.kafka.*`, `spring.mail.*` |
| Rails | `config/database.yml` `*.adapter`, `config/cable.yml` `*.adapter`, `config/storage.yml` `*.service`, `config/environments/*.rb` `cache_store` and `active_job.queue_adapter` |
| .NET | `appsettings*.json` `ConnectionStrings.*` |
| Node | a committed ORM/client config (`prisma/schema.prisma` `datasource.provider`, `knexfile.*` `client`, `ormconfig`/`data-source.ts` `type`) |
| Any | a compose `image:` on a service the app connects to |

Anything outside that table is not collected, even if it looks like a service. A framework absent from the
table contributes only through its env keys. Each stack file repeats its own row of this table under
`service_dependencies_documented`; the table here stays authoritative.

**"Maps to" means one of exactly these**, per collected name:
- A compose/devcontainer service in this repo whose name or `image:` matches the collected name or its driver (`REDIS_URL` to a `redis` service, `pgsql` to a `postgres` image).
- A **documented managed-service setup**: a committed doc that names the service, states it is externally hosted, and gives either the console/provisioning step or the exact config key to set. A bare mention of the product name is not documentation.
- A documented test fake or in-process substitute (a doc naming `sqlite`, `array`, `log`, `testcontainers`, `localstack`, `mailpit`, or the repo's own stub) for that name.

Skip only when the collection is empty.
PASS if ANY ONE of:
- Every collected name maps, per the three clauses above, with nothing left over.
- The setup doc lists each collected name with its local substitute and how to start it.

**Narrowed determinism caveat (this signal only).** Even with the extractor table finite, matching a name to
a service stays name-based, so a rename in the repo can move the verdict without the dependency changing.
Record the collected list verbatim in the rationale and mark the signal `determinism: narrowed` in the
report. A later run that collects a different list must show why from the diff. SKILL.md hard rule 1 points
here.

**`readme_setup_steps`** - repo scope, not skippable.
Fix: safe only when no `README.md` exists AND the four sections below can be filled from detected
evidence (resolved commands, the collected env-var set, the declared runtime); propose when a README
already exists, or when any section would be a placeholder.
PASS if ANY ONE of:
- `README.md` has a setup or getting-started section that covers all four of: prerequisites (a named runtime or tool with a version), install (one resolving command), config (an env file or config step), and run (one resolving command).
- The README links a `CONTRIBUTING.md` or `docs/` page that covers those same four.

A README that describes what the product does but never how to run it fails.

---

## Group 4: Codebase navigability (7 signals)

Agents read a fraction of a repo per task. Structure that is only in a maintainer's head is unavailable.

**`architecture_documented`** - repo scope, not skippable.
Fix: safe only when the stub is generated from real evidence - the repo's actual top-level source
directories, one line each - and no such file exists yet; propose otherwise. Hand the prose to `vd:docs`.
PASS if ANY ONE of:
- `docs/system-architecture.md`, `docs/architecture.md`, `ARCHITECTURE.md`, or an equivalent that names at least 3 paths that exist in the repo (or every top-level source directory, when there are fewer than 3) alongside what each holds.
- A `docs/decisions/` ADR set with at least one accepted record plus a document meeting the path-count clause above.
- The instruction file contains a directory map naming each top-level source directory and its purpose.

Fail a diagram with no file paths in it. An agent needs the mapping from concept to path.

**`module_boundaries_enforced`** - repo scope, **skippable**. Fix: propose - every passing clause is an
enforced check, and enforcement can fail a build on pre-existing code.
Skip for a single-module app with no internal layering claim.
Stack evidence: the `module_boundaries_enforced` row in each code-bearing stack's `stacks/*.md`.
PASS if ANY ONE of:
- Every code-bearing stack satisfies its own `module_boundaries_enforced` row.
- Any language: an automated check that fails when a declared boundary is crossed. Documentation alone does not pass.

**`dead_code_detection`** - app scope, not skippable.
Fix: safe when it adds a **new** tool config plus a **new** standalone runner script, touches no existing
config, and adds nothing to a committed manifest; propose when the tool must be added as a dependency,
when the rule belongs in an existing lint config, or when the repo enforces warnings-as-errors.
Stack evidence: the `dead_code_detection` row in each code-bearing stack's `stacks/*.md`.
PASS per app if ANY ONE of:
- Every code-bearing stack satisfies its own `dead_code_detection` row.
- Any language: a committed config for a named dead-code tool that a command or CI step invokes.

**`duplicate_code_detection`** - repo scope, not skippable.
Fix: safe under the same conditions as `dead_code_detection`; propose for a hosted-service config
(`.codeclimate.yml`, `sonar-project.properties`), which the service auto-discovers and starts acting on as
soon as it lands.
Stack evidence: the `duplicate_code_detection` row in each code-bearing stack's `stacks/*.md`.
PASS if ANY ONE of:
- Every code-bearing stack satisfies its own `duplicate_code_detection` row.
- A code-quality service config committed (`.codeclimate.yml`, `sonar-project.properties`) with duplication rules on.
- Any language: a committed duplicate-detection config a command or CI step invokes.

**`file_size_or_complexity_guard`** - repo scope, not skippable. Fix: propose. The rule lands in an
existing lint config, and a `warn` severity is not advisory under `--max-warnings=0`, `-Werror`, or
`TreatWarningsAsErrors`.
Stack evidence: the `file_size_or_complexity_guard` row in each code-bearing stack's `stacks/*.md`.
PASS if ANY ONE of:
- Every code-bearing stack satisfies its own `file_size_or_complexity_guard` row.
- Any language: a committed rule that reports files or functions over a named threshold.

**`naming_conventions_stated`** - repo scope, not skippable. Fix: propose - the enforcement clause gates a
build, and the documentation clause edits the instruction file or guidelines doc.
Stack evidence: the `naming_conventions_stated` row in each code-bearing stack's `stacks/*.md` names that
ecosystem's automated check.
PASS if ANY ONE of:
- An automated check: every code-bearing stack satisfies its own `naming_conventions_stated` row.
- The instruction file or a development-guidelines doc states, for at least 3 of the 4 categories - files, directories, types/classes, tests - either a named case convention (kebab-case, snake_case, PascalCase, camelCase) or a literal pattern (`*_test.go`, `*.spec.ts`).

"Use clear names" satisfies no category. Count the categories; do not rate the prose.

**`tech_debt_markers_tracked`** - repo scope, not skippable.
Fix: **safe** when it adds a new standalone scanner script and nothing else; propose when the fix adds a
lint rule to an existing config or a step to CI.
PASS if ANY ONE of:
- A committed CI step or script that inventories `TODO`/`FIXME`/`HACK`/`XXX` markers and reports the count or a trend.
- A lint rule that flags bare markers, per the `tech_debt_markers_tracked` row in the stack's `stacks/*.md`: eslint `no-warning-comments` with its `terms`/`location` options (it flags terms only - it cannot require an owner or an issue link), or ruff `TD002`/`TD003` (missing author, missing issue link), or a dedicated scanner enforcing the link policy. RuboCop `Style/CommentAnnotation` checks annotation *formatting* only and does not pass an owner-or-link policy on its own.
- The repo has zero such markers and a documented policy forbidding them.
- Any language: a committed mechanism that keeps the marker inventory visible rather than invisible.

---

## Branching and re-scoring

SKILL.md rule 8 isolates the **change**, not a specific branching ritual. The default is one branch per
signal group, named `readiness/group-<n>-<slug>`, so a rejected fix cannot block an accepted one.

| Situation | Do this |
|---|---|
| Dirty working tree | Stop before creating any branch. Report the dirty paths and ask the user to commit or stash. Never stash or discard their work, and never mix readiness fixes into an unrelated in-progress change. |
| Already on a feature branch | Branch the group branches off the current branch, not the mainline, and say so in the report. The user's in-flight work stays the base. |
| No remote | Local branches only. Skip every push and PR step; the report replaces the PR description. |
| Trunk-based, no branching allowed | Do not create branches. Apply one group at a time, re-score after each, and commit each group as its own single-purpose commit so it is revertible in isolation. Isolation of the change is preserved; only the mechanism differs. |
| Read-only sandbox | Preflight already downgraded `--fix` to `--report`. No branch, no commit, proposals only. |

**Re-scoring (SKILL.md rule 6) is per branch, never aggregated.** Each group branch gets its own real
re-run: the before-score (mainline, or the base branch) and the after-score **with that branch's fixes
applied and nothing else**. There is no combined after-score, because no branch holds every group's fixes,
and stacking branches to manufacture one destroys the isolation the branching exists for.

A proposal the user has not approved and applied changes no file, so it cannot move any score. Report
proposals in a separate **pending** list with the signal each would target and the delta it would produce
**if applied**, explicitly marked unverified. Never add a pending fix into an after-score.

---

## Report contract

The report is a Markdown file at the injected Reports path. **When no path is injected**, write
`agent-readiness-<as_of>.md` (for example `agent-readiness-2026-02-14.md`) into the directory the caller
names; with no directory either, print the same document to stdout. Never invent a location inside the
scanned repo - the report is an artifact about the repo, not a file the repo should acquire.

Percentages are rounded **half up to one decimal place** (`53.85` renders `53.9`), everywhere the number
appears. Sort keys, all deterministic: the signal table is in `id` order; the per-group table is in group
order 1 to 4; the ranked gap list is by group order, then `id` within a group. There is no other tiebreaker
and no severity judgement in the ordering.

```markdown
# Agent readiness: <repo name>

- as_of: <YYYY-MM-DD>
- commit: <short sha, or "no git history">
- apps (N=<n>): <path> [<code-bearing stacks>], ...
- score: <pp.p>% - Level <1-5>: <band reading>
- signals: <scored>/30 scored, <skipped> skipped

## Groups

| Group | Passed | Scored | Rate |
|---|---|---|---|
| 1 Agent instruction files | <sum of ratios> | <n> | <pp.p>% |
| 2 Verifiable feedback loops | ... | ... | ... |
| 3 Onboarding and environment | ... | ... | ... |
| 4 Codebase navigability | ... | ... | ... |

## Signals

| id | Group | Scope | Score | Evidence | Rationale |
|---|---|---|---|---|---|
| agent_config_committed | 1 | repo | 1/1 | `.mcp.json` | <=500 chars |
| ... (all 30, id order, `null` shown as `null` with the skip reason in Rationale) |

## Ranked gaps

| # | id | Group | Score | What is missing | Fix class |
|---|---|---|---|---|---|
| 1 | verification_baseline_green | 2 | 0/3 | no default-branch test run | propose |

## Applied fixes (--fix only)

Per branch: branch name, group, files created, commands run and their result, before-score, after-score.

## Pending proposals

Per proposal: signal id, the diff or checklist, and the delta if applied (unverified - not in any score).
```
