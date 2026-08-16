---
title: "Skills"
---

The catalog currently contains 77 skills under `skills/`. Each skill is self-contained and starts with a `SKILL.md` file. Optional scripts, references, and assets live inside the same skill directory.

Source: `find skills -mindepth 1 -maxdepth 1 -type d`, `scripts/validate.sh`.

Not sure where to start? `vd:guide` is the catalog's router - it maps a situation to the right skill or flow and carries the disambiguation rules for the overlapping clusters below.

## Core Delivery Flow

| Stage | Skills |
| --- | --- |
| Route | `vd:guide` |
| Discover | `vd:scout`, `vd:graphify`, `vd:research` |
| Decide | `vd:brainstorm` (diverge into options, grill to converge - Plannotator-first), `vd:scenario` |
| Plan | `vd:plan` (phased plan + Definition of Done; `--audit` for an independent clean-context check) |
| Execute | `vd:cook`, `vd:fix`, `vd:debug`, `vd:tdd`, `vd:codex-workflow` |
| Review and ship | `vd:code-review` (incl. `--refactor` fit/slop lens), `vd:simplify` (incl. `--aggressive` reshape and `--scan` survey), `vd:security`, `vd:miucr`, `vd:ship`, `vd:git` |
| Iterate | `vd:auto-loop`, `vd:optimize-loop` |
| Orchestrate | `vd:ultracook` |

`vd:ultracook` is the conductor over the stack: it classifies a task (direct / pipeline / fan-out), composes the needed slice of **brainstorm → plan → cook → review → ship** as stages with checkable done-when gates, and runs to a verified terminal state with resumable on-disk state. Each stage's discipline lives in the invoked skill - ultracook is a map, not a cage.

Where [Plannotator](https://plannotator.ai) is installed, plan approval rides its plan-review hook (annotate in the browser, structured feedback back to the agent), and `vd:brainstorm` delivers its grilling rounds as annotatable briefs via `plannotator-annotate`.

## Agent And Tooling Skills

| Area | Skills |
| --- | --- |
| Browser automation and e2e | `vd:ego-browser`, `vd:browser`, `vd:browser-profile`, `vd:browser-trace`, `vd:agent-browser`, `vd:web-e2e`, `vd:web-perf` |
| Web and frontend | `vd:uiuxdesign`, `vd:opendesign`, `vd:fastreact` |
| Design contracts | `vd:apidesign` (owns the deep-module design vocabulary), `vd:dbdesign` |
| Docs and diagrams | `vd:docs`, `vd:tech-docs`, `vd:diagram`, `vd:text-diagram`, `vd:excalidraw`, `vd:tldraw-offline` |
| Media, files, and social | `vd:omnimedia`, `vd:marketing-design`, `vd:copywriting`, `vd:show-off`, `vd:file-browser`, `vd:twitter`, `vd:devlog` |
| Product CLIs | `vd:miucr` (AI code-review CLI), `vd:miudb` (database CLI), `vd:vd-cli` (skill manager), `vd:cli-ts` (build your own) |
| SaaS and workspace operations | `vd:gws`, `vd:jira`, `vd:smartsheet`, `vd:braze`, `vd:voice-agent`, `vd:superwhisper` |
| Local operations and isolation | `vd:worktree`, `vd:herd-worktree`, `vd:herdr`, `vd:gopass`, `vd:computer-clean`, `vd:journal`, `vd:workbench` |
| Personal ops | `vd:issue-invoice`, `vd:resume-screen` |
| Skill lifecycle | `vd:skill-creator`, `vd:skill-management`, `vd:skill-audit`, `vd:rule-miner`, `vd:skill-evolve` |
| Repository readiness | `vd:agent-readiness` |

Within the skill lifecycle, `vd:skill-creator` authors a brand-new skill (description routing, hard rules, verification, and the writing-for-agents principles in its `references/writing-principles.md`); `vd:skill-management --create` delegates to it where the runtime supports invoking another skill (Claude Code) and otherwise falls back to the `scripts/new-skill.sh` scaffold, and `vd:skill-management` owns the surrounding mechanics - scaffolding, vendoring via `vd`, frontmatter validation, and releases. `vd:skill-evolve` improves skills that already exist from the current session, `vd:skill-audit` reports which skills actually get used, and `vd:rule-miner` distils repeated corrections into `CLAUDE.md` rules.

`vd:agent-readiness` scores a repository against a fixed 30-signal rubric - agent instruction files, verifiable feedback loops, onboarding reproducibility, and codebase navigability - then applies the additive fixes that are safe and proposes the rest. It owns the score and the remediation plan and hands the writing to `vd:docs` and `vd:skill-creator`.

Inside Herdr, `vd:worktree` delegates current-pane naming to `vd:herdr` after a successful create, using a short `<project>:<intent>` label.

`vd:computer-clean` also audits Git worktree storage and supports the reusable `clean merged` and `clean all` approval modes through `vd:worktree`.

Within browser automation, `vd:ego-browser` drives logged-in browsing through isolated ego lite task spaces, follows the active app's embedded runtime contract, and asks before closing each completed space so short tasks do not leave clutter behind. `vd:agent-browser` is the direct CDP driver for the persistent Chrome that `vd:browser-profile` launches, and keeps its own video-recording and network-mocking specialties. `vd:browser-trace` captures vendor-free raw-CDP traces (console, network, lifecycle) against that same local Chrome. `vd:browser` is scoped to Browserbase cloud sessions only - the escalation target for CAPTCHA, anti-bot, and proxy work when a local run hits a wall. `vd:web-e2e` orchestrates logged-in end-to-end flows on top of them.

`vd:miucr` operates the `miucr` AI code-review CLI - staged/PR reviews, MCP server mode, webhook daemon, and evals - as an alternative review surface to `vd:code-review`'s inline-comment flow.

`vd:jira` uses the `vanducng/jira-cli` fork for native inline local-image comments, accepts `--project` and `--type bug|task` for untracked local rules, and maps board columns to verified workflow transitions.

## Language And Migration

| Area | Skills |
| --- | --- |
| Go | `vd:golang` (idiomatic guidance by topic), `vd:gostack` (opinionated samber/* library stack) |
| Migration | `vd:py2go` (Python-to-Go playbooks) |
| TypeScript | `vd:cli-ts` (production CLI architecture) |

`vd:golang` consolidates idiomatic Go guidance - style and naming, error handling and safety, concurrency and performance, testing and CI, project layout and dependencies, and observability and gRPC - routing by topic to `skills/golang/references/`. `vd:gostack` is an opinionated reference for Sam Berthe's Go libraries (`lo`, `oops`, `do`, `mo`, `slog`, `hot`, `ro`), with per-library notes under `skills/gostack/references/`. `vd:py2go` runs end-to-end Python-to-Go migrations with six project-type playbooks and pinned stack defaults.

## Infrastructure And Deployment

| Area | Skills |
| --- | --- |
| Cloud and platforms | `vd:aws`, `vd:devops` |
| Data platforms | `vd:cnpg` (CloudNativePG on K8s), `vd:astro-airflow` (Astro/Airflow deployments) |

`vd:aws` operates AWS accounts and services through the official CLI with identity-first scoping, cross-service incident tracing, focused references for serverless, compute/networking, observability/storage, explicit mutation boundaries, and a gopass-backed `reset-password` workflow.

`vd:devops` covers deployment and infrastructure operations - Docker and Docker Compose, Kubernetes (`kubectl`, Helm, RBAC), Terraform/OpenTofu, cloud platforms (GKE/EKS, Cloud Run, Cloudflare Workers/R2/D1), GitHub Actions CI/CD, and GitOps (Argo CD, Flux) - with per-topic notes under `skills/devops/references/`.

## Choosing The Right Skill

`vd:guide` carries the full routing map; the short form:

Use `vd:scout` when you need a map, `vd:debug` when behavior is failing (repro-first, ranked hypotheses), `vd:brainstorm` when the approach is undecided (or `--grill` to sharpen an existing idea by interview), `vd:plan` when the implementation path is not yet concrete, `vd:cook` when a plan is ready to execute, and `vd:ship` when the work is tested and ready for remote.

Within review, the lenses answer different questions: `vd:code-review` asks whether a change is ready to land (two parallel axes - spec fidelity and standards - posted as inline PR comments; `--refactor` stays local and asks whether the change fits the codebase or reads as slop), `vd:simplify` reduces reading complexity with behavior frozen (`--aggressive` reshapes a working feature into the form it should have had from day one, deleting compatibility paths only after proving them dead; `--scan` surveys the codebase for refactor candidates), `vd:security` threat-models the change, and `vd:plan --audit` independently audits a plan before execution.

`vd:tdd` holds the testing discipline - what a good test is, pre-agreed seams, red-before-green, and the anti-patterns (implementation-coupled, tautological, horizontal slicing). `vd:cook --tdd`, `vd:fix`'s regression guard, and `vd:plan --tdd` compose it.

Use `vd:docs` for canonical internal project docs, ADRs (behind the three-part gate: hard to reverse AND surprising AND a real trade-off), and the optional domain glossary. Use `vd:tech-docs` to create, modernize, validate, and ship a rendered public developer documentation site.

Use `vd:superwhisper` to search local dictation history, prepare standups or commitment reviews, diagnose pronunciation and raw-versus-processed transcription errors, detect unwanted short-input expansion, and maintain vocabulary or snippets with approval. Invoke `vd:superwhisper --pronunciation <term>` for repeated recognition errors or `vd:superwhisper --diagnose <term-or-recording-id>` for processing failures.

Use `vd:braze` for category-first Braze reads, leaf-permission diagnosis, explicit opt-in or opt-out changes, and end-to-end `braze-cli` validation.

Use `vd:smartsheet` to discover and read sheets with bounded JSON commands, then perform only explicitly authorized row additions or updates with read-back verification.

Use `vd:voice-agent` to operate Retell through `vac` with bounded reads, explicit write authorization, current endpoint guidance, and structured recovery.

Use `vd:tldraw-offline` to inspect, edit, persist, and verify canvases in the local tldraw desktop app. New canvases default to the injected feature visuals directory, with structural, persistence, and conditional visual completion gates.

`vd:resume-screen` scores operator-supplied resumes against a JD into an Excel workbook (knockouts, a 100-point factor `Total` that is an Excel formula, overlays, fact-check). Role scorecards are profiles under the skill - add a new role with a profile file and one index row, not a fork of the skill. The operator provides the JD and resume files; the skill does not pull from Google Drive or LinkedIn Recruiter. Logged-in fact-check composes `vd:ego-browser`, or a named `vd:browser-profile` driven by `vd:agent-browser` in connect mode (`vd:browser` only if LinkedIn/GitHub anti-bot blocks the local profile).
