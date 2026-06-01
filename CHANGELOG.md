# Changelog

All notable changes to this repo are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow [SemVer](https://semver.org/).

## [Unreleased]

### Added
- Release Please workflow for SemVer skill-catalog releases. The release PR
  bumps `version.txt`, `skills.toml`, `.claude-plugin/plugin.json`, and
  `.claude-plugin/marketplace.json` together, with CI checking version
  consistency.
- `skills/file-browser/` — CSV/TSV/XLSX files now render as tabular data in `/view` instead of falling through to source text. CSV/TSV parsing handles quoted commas and quoted newlines; XLSX renders the first worksheet using `read-excel-file`. Gallery, sidebar tree classification, MIME types, docs, and smoke tests were updated for table files.
- `skills/sqlit/` — scriptable CLI wrapper over the `sqlit` binary for ad-hoc SQL against any saved connection (BigQuery, Postgres, MySQL, MSSQL, SQLite, Snowflake, DuckDB). Encodes the shell-quoting gotcha (single-quote SQL with backticks so the shell doesn't eat them), the bare-`sqlit` TUI hazard, per-dialect metadata recipes, and the failure-mode → cause map. Lets `vd:` workflows hit databases without re-deriving these rules each time.
- `skills/optimize-loop/` — autonomous metric-optimization loop (autoresearch pattern: Modify→Verify→Keep/Discard→Repeat). Runs N bounded iterations against a mechanical metric (coverage, bundle size, lint/type errors, latency, LOC), commits each attempt before verifying, auto-keeps wins and `git revert`s regressions. Protocol-only (no scripts), with references for the 8-phase loop, noise-aware verification + guard, git-as-memory + TSV results log, and a copy-paste metric library. Complements `vd:auto-loop` (goal-pursuit) — different exit philosophy (metric/stuck-detection vs two-vote gate). Includes a verify-command safety screen + credential masking.
- `skills/diagram/` — `--versioned` mode now writes git-trackable diagram artifacts under `docs/diagrams/<slug>/` (`diagram.spec.yaml`, `manifest.json`, `prompt.md`, `meta.json`, `vN.svg|png`). Added first-class `workflow` / `wf` / `process` diagram type with skeleton layout support, workflow type references, fixture coverage, and unit tests for versioned artifact writers.
- `skills/scenario/` — edge-case generation by decomposing a feature/file across 12 risk dimensions (boundary, null, concurrency, authz, IO failure, time, encoding, …). Default one-shot pass; `--saturation` iterates (bounded) until coverage converges. Output is a severity-tagged scenario report for QA/test design, not executable tests.
- `skills/security/` — STRIDE + OWASP threat-modeled audit scanning from multiple attacker perspectives, with an optional bounded `--red-team` discovery loop and an autoresearch-style `--fix` loop (reuses `vd:optimize-loop`'s protocol). Defensive/authorized use only; mandatory credential masking on all findings and PoCs.

### Fixed
- Skill cross-references now use canonical skill IDs instead of hard-coded invocation prefixes, for example `vd:cook plans/path/to/feature`. Codex users add the dollar prefix when invoking; Claude Code users add the slash prefix.

### Removed
- `tools/vd/` — `vd` CLI extracted to standalone [`vanducng/vd-cli`](https://github.com/vanducng/vd-cli) at `v2.0.1`. Module path renamed `github.com/vanducng/skills/tools/vd` → `github.com/vanducng/vd-cli/v2` (Go SIV-compliant). Homebrew install path unchanged (`brew install vanducng/tap/vd`). Skills repo now skills-only.
- `.github/workflows/vd-test.yml`, `vd-release.yml`, `vd-release-please.yml` — moved to `vanducng/vd-cli`.
- `.release-please-config.json`, `.release-please-manifest.json` — only tracked `tools/vd`; skills bundle releases continue to be cut manually.
- `install.sh` (root) — stale `vd` binary downloader pointing at `vanducng/skills` GH releases. Binary lives in `vanducng/vd-cli` now; install via `brew install vanducng/tap/vd` or `go install github.com/vanducng/vd-cli/v2/cmd/vd@latest`. README updated to drop the curl-pipe line and the dead `tools/vd/README.md` link; `scripts/install.sh` retained as the dev-only fallback symlinker.

### Changed
- `skills/excalidraw/SKILL.md` 1.0.0 → 1.1.0 — added compact legend guidance for diagrams where colors, shapes, stroke styles, or arrow colors encode meaning. Diagrams now cap active semantic colors at 5, merge similar components into shared color families, and keep legends to 3-5 used semantics so they explain the diagram without becoming clutter.
- **Project framing de-personalized** — bundle/marketplace/plugin descriptions, README, and AGENTS.md now read "a daily-driver collection of skills for agentic coding" (was "Duc's personal Claude Code skills"). `code-review` description: "personal review style" → "opinionated review style". `[meta].description` + `[targets.claude.bundle].plugin_description` are now set in `skills.toml` so `vd build` keeps the generated `.claude-plugin/*.json` de-personalized. `author`/owner attribution metadata and repo URLs unchanged.
- `skills/fix/SKILL.md` 1.0.0 → 1.1.0 — added a **regression-decision gate** (when the blast-radius sweep finds a side effect: STOP, present what broke + why + 2–4 options via `AskUserQuestion`, never silently patch — hard stop even in `--auto`) and a **scout-before-questions** gate (state a 3–6 bullet codebase-context summary before asking anything). Adapted from claudekit's fix `HARD-GATE-NO-SIDE-EFFECTS`; new content in `references/verify-and-prevent.md`.
- **Marketplace renamed `vanducng-skills` → `vd-skills`** in `.claude-plugin/marketplace.json`. Install command shortens to `/plugin install vd@vd-skills`. **Breaking for existing users**: migrate via `/plugin marketplace remove vanducng-skills && /plugin marketplace add vanducng/skills && /plugin install vd@vd-skills`. Plugin cache path also moves from `~/.claude/plugins/cache/vanducng-skills/` to `~/.claude/plugins/cache/vd-skills/` (Claude Code handles this transparently on re-add). README + `skills/open-design/SKILL.md` doc comment updated to match.
- `skills/skill-management/SKILL.md` — `--release` mode redirects to `vanducng/vd-cli`; install instructions point to the new repo.
- `skills/cook/SKILL.md` — added a **Pragmatism rules** section encoding YAGNI/KISS/DRY for execution: Rule of Three before extracting (Sandi Metz), no speculative generality (Fowler/YAGNI), inline > one-liner helpers, no throwaway comments (no `// TODO: refactor later`, version tags, commented-out code), MVP/POC bias. Removed duplicated `Quality bar` and `Output rules` sections (subsumed by Hard rules + Modes table) and unverifiable stats. Reviewer prompt now also flags premature abstractions + throwaway comments. Bumped 1.0.0 → 1.1.0.
- `skills/git/references/pr-template.md` — added **Brevity rules** with section-length table, anti-patterns, and a before/after example. Clarifies how the conceptual section names map onto the repo-template heading style vs. the fallback bullet style so an LLM doesn't mix both.

## [0.12.0] - 2026-05-21

### Added
- `skills/code-review/` — personalized PR review skill. Borrows the inline-comment posting workflow from upstream `review-pr` and folds it into a vd: skill with a personal review voice. PR mode is the polished path: a single `gh api POST /pulls/:n/reviews` call builds the entire review payload (top-level summary + inline comments anchored to the PR head SHA). Severity prefixes (`Critical / Important - <topic> / Suggestion / Question / Nit`), comment shape (problem-first, evidence, concrete alternative), and tone calibration (encouraging when earned, direct on real problems, never condescending). Reference example shape: `careernowbrands/cnb-data-contract#124`. Other modes (`--pending`, commit hash, codebase) kept lean. Project-specific rules deferred to `CLAUDE.md` / `docs/code-standards.md` so the skill stays repo-agnostic.
- `skills/browser-profile/` — named persistent Chrome profile registry on top of `--user-data-dir` + `--remote-debugging-port`. Lets the user and Claude both attach to the *same* Chrome window across runs without `--user-data-dir` collisions. Six verbs: `profile-list`, `profile-open`, `profile-attach`, `profile-close`, `profile-export`, `profile-reset`. Pairs with `vd:browser` (`browse env local --auto-connect`) for the CDP attach step.

### Changed
- `skills/browser/` + `skills/browser-trace/` — synced from `browserbase/skills@b2ae728` (upstream bump, no behavioural changes on our side).

## [0.11.0] - 2026-05-14

### Added
- `skills/git/` — granular git toolkit: stage / commit / push / PR / merge as discrete verbs (`cm` / `cp` / `pr` / `merge`). Delegates verbose ops to `git-manager` subagent; `--inline` keeps them in main context. Conventional commit format with secret-scan block, auto-split heuristic, pre-commit lint, pre-push test gate, remote-first diff for PRs, branch-protection rules.
- `skills/git/references/pr-template.md` — canonical PR title + body conventions, shared with `vd:ship`. Past-tense (v-ed) title rule (`feat(auth): added OAuth2 provider`) to distinguish PR titles from commit-message imperatives; ticket-prefix detection; repo-template-wins priority; Why / What / Risks + verification stripe fallback body; per-bullet fill rules; worked examples.
- `skills/docs/` — keep `./docs/` honest with `init` / `update` / `check` verbs over a canonical small set (`README.md`, `development-guidelines.md`, `system-architecture.md`, `tech-stack.md`, `deployment.md`). Scouts the codebase, delegates writing to `docs-manager` subagent (or `--inline`). `--dry-run` prints the plan without writes. Out-of-scope by design: changelog, roadmap, codebase-summary, PRD — those rot fastest and `vd:ship` / `vd:journal` already cover them.
- `skills/twitter/` — Twitter / X CLI skill (login / post / thread / reply / fetch / timeline / delete / doctor / import-from-dia) backed by `twikit` with browser-cookie fallback. Loads credentials from gopass (`personal/x-twitter/credentials`). Test suite (router / formatters / media / url-parser / dia-cookies / twikit patch) plus integration smoke script.
- `skills/brainstorm/assets/comparison-template.html` (v1.3.0) — self-contained interactive draft template for visual brainstorming. Wireframe CSS vocabulary inlined (`.options`, `.cards`, `.mockup`, `.split`, `.pros-cons`, `.mock-nav` / `-sidebar` / `-content` / `-button` / `-input`, `.placeholder`), light + dark theme tokens, cosmetic click-to-highlight, no server / no event polling. Drafts save to `{plan_dir}/visuals/brainstorm-{slug}/comparison-{N}.html` per existing artifact convention; never overwrite, never under hidden dotdirs.

### Changed
- `skills/ship/references/pr-template.md` — slimmed to a thin pointer at `skills/git/references/pr-template.md` (canonical) plus ship-specific Step-12 / Step-14 integration notes. Title format, body shape, per-bullet fill rules, and worked examples now live in one place.
- `skills/brainstorm/` v1.2.0 → v1.3.0 — added Visual draft mode (when the question is genuinely visual, render A/B/C panels alongside text options for the user to react to shapes, not just words); brief self-review checklist (placeholder / consistency / scope / ambiguity / divergence — fix inline before handoff); explicit user review gate before invoking `vd:plan`; one-question-at-a-time + multiple-choice-preferred discipline for Phase-1 clarifying questions; handoff matrix after pick: `vd:open-design` (polished pages), `vd:diagram` (rendered diagrams), `vd:excalidraw` (whiteboard sketches). Borrows the CSS vocabulary from `obra/superpowers` visual-companion without the server / event-polling machinery — user replies in chat, not via DOM events.
- `skills/ship/` v1.1.0 → v1.2.0 — `--auto` on-target-branch recovery. Previously `--auto` on `main` would still prompt with the 3-option dialog ("create feature branch / direct push / abort"). Now in `--auto`: auto-create `feat/<slug>` from inferred slug (staged-diff filenames → commit subject → `auto-{timestamp}` fallback), prefix-by-mode (`feat/` for official, `release/` for staging, `dev/` for beta), continue the pipeline silently. Direct-push to target stays interactive-only — never available in `--auto`. Hard Rule 8 safety floor clarified to enumerate which preflight conditions are auto-recoverable vs which always stop the pipeline.

## [0.9.0] - 2026-05-10

### Added
- `skills/scout/` — fast, parallel codebase scouting across software, data-engineering, devops, and analytics surfaces. Locates files, dbt models, dashboards, IaC, pipeline DAGs, K8s manifests, secrets, and CI workflows before changes. Internal mode (Explore subagents) and external mode (Gemini / OpenCode CLI) with model overrides via `GEMINI_MODEL` / `OPENCODE_MODEL` env vars.
- `skills/scout/references/domain-scouting.md` — search-target playbooks per discipline: dbt lineage tracing, env-var maps across the stack (app → container → K8s → IaC → secrets → CI), BI metric-to-source tracing.
- `skills/debug/` — systematic debugging across software, data pipelines, infrastructure, and analytics. Iron law: no fixes without root cause investigation first. Loads references on demand: systematic-debugging, root-cause-tracing, defense-in-depth, verification, investigation-methodology, log-and-ci-analysis (incl. K8s + dbt), performance-diagnostics (incl. BigQuery / Snowflake / Spark), reporting-standards, frontend-verification, task-management-debugging.
- `skills/debug/references/data-pipeline-debugging.md` — dbt run/test failures, source-freshness, schema drift, idempotency check, backfill discipline, Airflow / Dagster / Prefect entry points, Spark stage skew, streaming consumer lag.
- `skills/debug/references/infrastructure-debugging.md` — K8s pod-won't-start triage, Docker reproducibility, multi-environment configuration diff (Helm / Kustomize / Terraform), secret rotation, IaC drift, networking, cloud-provider quick checks.
- `skills/debug/references/data-analytics-debugging.md` — wrong-number top-down trace (dashboard → BI SQL → semantic layer → mart), fan-out join detection, metric drift across dashboards, BI cache / refresh issues, schema-change-broke-the-chart, time / timezone bugs, conformance issues.

### Changed
- `skills/brainstorm/SKILL.md` (1.0.0 → 1.1.0) — workflow position now points to `vd:scout` and `vd:debug`. Added "Cross-discipline cues" section that biases Phase-1 framing per discipline (software / data engineering / devops / analytics) so the three options diverge along the axes that matter for that surface.

## [0.8.0] - 2026-05-08

### Added
- `skills/ship/` — ship pipeline skill: pre-flight → link issues → merge target → tests → review → version bump → changelog → journal → docs → commit → push → PR (→ optional release tag).
- Three ship modes: `official` (main/master), `staging` (staging/uat/release/x.y.z), `beta` (dev/development/beta) — each maps to a different target branch and skip-set.
- `--release` flag to cut a GitHub release at the end. Tag style adapts per mode: stable `vX.Y.Z` (official), `vX.Y.Z-rc.N` prerelease (staging), `vX.Y.Z-beta.N` prerelease (beta).
- Auto-release detection (`goreleaser`, `release-please`, `semantic-release`, `changesets`, CI workflow) — when present, Step 13 lets CI tag instead of doing it manually.
- `--auto` flag for fully autonomous shipping — answers prompts with safe defaults and queues `gh pr merge --auto`. Safety floor: still stops on critical review issues, secret leaks, test failures, merge conflicts, and red CI.
- CI watch step (always runs after PR creation): waits for `gh pr checks` to settle (15-min cap); on red CI prompts the user even under `--auto` (investigate / merge anyway / abort); on still-pending lets `--auto` queue via `gh pr merge --auto`.
- PR title rule: ticket prefix in branch (`PRJ-123-…`) → `PRJ-123: <past-tense description>`; otherwise conventional `type(scope): …`.
- PR body source priority: project's `.github/pull_request_template.md` wins, else built-in fallback template.
- Lean fallback PR template: three labelled bullets (**Why** / **What** / **Risks**) plus a single italic verification stripe (`_Tests: ✓ N · Docs: ✓ · Breaking: –_`). No section headings — eliminates Summary/Changes overlap by construction. **What** nests when >3 behavior shifts. Per-bullet AI-fill sources documented in `skills/ship/references/pr-template.md`. Step 14 (CI watch) now refreshes the verification stripe in-place via `gh pr edit` once CI is green so reviewers see live status, not commit-time claim.

## [0.7.0] - 2026-05-08

### Added
- `skills/omnimedia/` — multimodal AI skill: Gemini for analysis (vision/transcribe/OCR/extract); image generation via Codex (ChatGPT subscription), Gemini/Imagen, OpenRouter, MiniMax; video, speech, music via Gemini + MiniMax.
- `--provider codex` — image-gen provider that shells out to `codex exec "$imagegen ..."`, billed against ChatGPT subscription quota (no `OPENAI_API_KEY`). Standalone CLI: `scripts/codex_imagegen.py`. PNG capture via tmpdir glob with `-o/--output-last-message` as a secondary path.
- `--provider auto` cascade reordered for image gen: **Codex → Google → OpenRouter → MiniMax**. Codex is tried first (subscription-free); on `CodexQuotaExceeded` / `CodexNotAvailable` / `CodexError`, falls through to existing paid paths. Routing decision logged to stderr (`[auto] using <provider>`).
- `references/codex-imagegen.md` — setup, model semantics (`-m` is Codex base model, not image), quota math, latency, cascade behavior, live-smoke command.
- `scripts/tests/test_codex_imagegen.py` — mocked + gated live tests (`OMNIMEDIA_SMOKE_CODEX=1`).
- `scripts/tests/test_provider_routing.py` — covers explicit-codex, auto-first-codex, quota-fall-through, codex-unavailable-silent, and image-gen-only routing.

### Changed
- `check_setup.py` — adds Codex CLI presence + ChatGPT login status check (non-fatal).

## [0.6.0] - 2026-05-05

### Added
- `tools/vd/` — Go CLI for tracking, vendoring, and publishing Claude skills. Introduces `skills.toml` manifest, `skills.lock`, and verbs: `init`, `add`, `list`, `sync`, `update`, `diff`, `doctor`, `pin`, `detach`, `remove`, `build`, `cache clean`. Distributed via GoReleaser (tag prefix `vd/v*`), Homebrew tap, and `install.sh`.
- `marketplace.json` and `plugin.json` are now regenerated by `vd build` in default bundle mode.
- `.agents/` symlink directory emitted by `vd build` for agent-context tooling.
- `skills/browser/` and `skills/browser-trace/` — vendored from `browserbase/skills` via the new CLI workflow (first tracked-mode upstream skills under the `vd:` namespace).

## [0.5.1] - 2026-05-04

### Changed
- `skills/excalidraw/` — Step 0 now auto-bootstraps `.mcp.json` at the project root (using the project folder name as `X-Tenant-Id`) when neither the Excalidraw MCP tools nor the REST fallback are available. Merges into existing `.mcp.json` without clobbering other servers.

## [0.5.0] - 2026-05-04

### Added
- `skills/open-design/` (v1.0.0) — generate single-file HTML design artifacts (landings, dashboards, mobile screens, decks/PPT, posters, social carousels, emails, e-guides, …) by composing 60 production skills × 137 brand-grade design systems sourced from [github.com/nexu-io/open-design](https://github.com/nexu-io/open-design).
  - `open-design sync` — sparse-clone or `git pull` upstream into `~/.cache/$USER-open-design`. Offline-tolerant (falls back to cache silently). Per-user namespace via `$USER`.
  - `open-design search "<prompt>"` — ranks top 5 skills + top 5 design systems for a free-form design brief. Auto-routes between two engines:
    - **qmd path** (when `qmd` is on `PATH`): per-token `qmd search` (BM25, no model download) + 5× name-match bonus to overcome qmd's strict multi-token AND semantics; vote-aggregated across tokens.
    - **grep fallback** (no qmd): frontmatter-weighted token overlap (5× name, 3× triggers/category, 1× body) with stopword filter — works for the curated 197-doc catalog without external deps.
  - `open-design list / show / preview` — list catalog, resolve cache paths, open generated artifact in browser via `open`/`xdg-open`.
  - SKILL.md prescribes a 6-step workflow: sync → search → resolve paths → read upstream SKILL.md + assets/template.html + references/layouts.md + DESIGN.md → compose → preview. Hard rules: never invent CSS classes, never write sections from scratch, never use off-palette tokens, single self-contained HTML file, no filler copy.
  - Bash CLI is bundled inside the skill folder (291 lines) — works from dev clone, plugin cache, or user-level install. Zero hard dependencies beyond git/bash/grep/awk.
- `skills/qmd/` (v1.0.0) — wrapper skill teaching Claude how to use the [tobi/qmd](https://github.com/tobi/qmd) Markdown search CLI properly. Approach guidance acknowledged from [levineam/qmd-skill](https://github.com/levineam/qmd-skill).
  - Default to `qmd search` (BM25, instant, no model). Escalate to `qmd vsearch` only when keywords fail. Avoid `qmd query` unless user accepts a 1.28GB model download for marginal quality gain.
  - Recipes for `--files`, `--json`, `--all --min-score`, multi-token vote-aggregation, `qmd get` / `multi-get`, maintenance via `qmd update`/`embed`.
  - Composes with `vd:open-design` — open-design auto-detects qmd and routes through it for catalog search.

## [0.4.0] - 2026-05-04

### Added
- `skills/brainstorm/` (v1.0.0) — solution-space exploration skill, replaces `ck:brainstorm`:
  - Three-way distinction from `vd:research` (compare known options) and `vd:plan` (sequence steps).
  - Modes: `--quick` (chat-only), default (decision brief), `--deep` (red-team round + failure-mode catalog + migration paths).
  - 5-phase flow (Frame → Diverge → Stress-test → Converge → Brief) with mandatory scope-decomposition gate.
  - Forced-divergence rule: 3+ options must violate each other's architectural assumptions; "X with Postgres / X with MySQL" counts as one option.
  - Steel-man-before-strawman requirement; per-option dealbreaker scenario, hidden cost, reversibility cost.
  - Concrete output template with TL;DR, comparison matrix, and Open Questions section.
- `skills/plan/` (v1.0.0) — phased implementation planning skill, replaces `ck:plan`:
  - Self-contained — no ClaudeKit CLI dependency; standard Claude Code tools only (Agent, WebSearch, Read/Write).
  - Modes: `--quick` (single inline-phases plan.md), default (plan.md + per-phase files), `--deep` (research dispatch + red-team review).
  - `--tdd` composable flag — tests-first structure in every phase.
  - 6-phase flow (Frame → Discover → Design → Write → Hand off → Red-team) with mandatory scope-decomposition gate.
  - Hard rules: phases must be independently reviewable, files must be named, success criteria must be observable.
  - Specials for migrations, breaking-change sequencing, performance baselines, refactors, library upgrades.
- `skills/cook/` (v1.0.0) — phased implementation execution skill, replaces `ck:cook`:
  - Self-contained — no ClaudeKit CLI dependency, no Claude Tasks requirement; uses generic `Agent` subagent calls for testing/review.
  - Modes simplified to 3: `--quick` (sub-plan tasks), default (per-phase review gates), `--auto` (continuous run).
  - Composable: `--tdd` (failing tests before implementation), `--no-test` (loud-warn).
  - Per-phase 7-step loop: Conform → Implement → Verify → Test → Review → Update status → Gate.
  - Hard rules: one phase at a time, compile per file, plan-status-truthful per phase, no silent design decisions, kick back to `vd:plan` if plan is wrong.
  - Specials for migrations, breaking changes, performance baselines, UI manual checks, library upgrades, bug-fix-with-failing-test-first.

### Pipeline
- The `vd` plugin now ships an end-to-end build pipeline: `vd:brainstorm` → `vd:plan` → `vd:cook`. Each skill cross-references the next and explicitly kicks back when the prior decision is wrong (e.g. cook → plan if plan is wrong; plan → brainstorm if approach is wrong).

### Changed
- `skills/markdown-render/` — added custom logo (`assets/logo.png`, 1024×1024) and `assets/favicon.png` (open-book + markdown hash, warm cream + saddle-brown palette). Includes `scripts/generate-logo.cjs` for regeneration via OpenRouter.

## [0.3.0] - 2026-05-04

### Added
- `skills/excalidraw/` (v1.0.0) — Excalidraw MCP diagram skill for technical diagrams:
  - Domain styling presets with hex palettes for **software architecture (C4 / microservices)**, **cloud architecture (AWS / GCP / Azure)**, **data pipelines / ETL / lakehouse**, **UML (sequence / ER / state / class)**, and **deployment (Kubernetes / Docker)**.
  - Sizing formulas (rectangle / diamond / ellipse) accounting for Excalidraw font width, arrow visibility rules (≥120px gap), two-batch ordering (shapes → arrows), and the mandatory write-check-review verification loop.
  - Quality checklist, anti-patterns table, MCP tool quick reference (32 tools), and edge-style conventions (batch / stream / async / lineage).
  - `references/styling-presets.md` — full color tables, layout templates (3-tier, event-driven, Lambda architecture, ELT lakehouse, microservice mesh, C4 skeleton), accessibility palette, implementation checklist.
  - `references/cheatsheet.md` — MCP vs REST format differences, element property reference, common recipes (arrow binding, translucent zones, cylinder approximation), verification loop.

## [0.2.0] - 2026-05-03

### Changed
- **Restructured as a Claude Code plugin (`vd`).** Skills now install via `/plugin install vd@vanducng-skills` and appear in the catalog as `vd:<skill>` (e.g. `vd:research`, `vd:computer-clean`).
- `marketplace.json` now registers a single plugin `vd` pointing to this repo as source.
- README rewritten around the plugin install flow; symlink `install.sh` retained as a dev-only fallback (skills installed that way appear without the `vd:` prefix).

### Added
- `.claude-plugin/plugin.json` — plugin manifest for `vd`.
- `skills/research/` (skill v2.0.0) — deep technical research skill:
  - WebSearch only (Gemini path removed).
  - **`--deep` flag** for high-stakes decisions: query budget 5 → 12, expanded report with failure-modes table, migration paths, operational war stories, performance-under-realistic-load, decision reversibility.
  - Multi-option evaluation is mandatory — single-option reports flagged as failure.
  - Comparison matrix non-optional in any mode.
  - Reports save to CWD as `research-{slug}-{YYYYMMDD}.md`.
  - YAGNI/KISS/DRY explicitly overridden in favor of depth, brutal honesty, and answering the user's actual demand.

### Removed
- `skills/hello-world/` — smoke-test skill, no longer needed now that the plugin install path is verified.

## [0.1.0] - 2026-05-03

### Added
- Initial repo scaffold.
- `scripts/install.sh` — per-skill symlink installer (idempotent, conflict-safe).
- `scripts/uninstall.sh` — removes only repo-owned symlinks.
- `scripts/new-skill.sh` — scaffolder for new skills.
- `scripts/validate.sh` — frontmatter linter.
- `.claude-plugin/marketplace.json` — marketplace stub.
- `skills/hello-world/` — smoke-test skill.
- CI: `.github/workflows/validate.yml`.
