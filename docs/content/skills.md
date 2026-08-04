---
title: "Skills"
---

The catalog currently contains 76 skills under `skills/`. Each skill is self-contained and starts with a `SKILL.md` file. Optional scripts, references, and assets live inside the same skill directory.

Source: `find skills -mindepth 1 -maxdepth 1 -type d`, `scripts/validate.sh`.

## Core Delivery Flow

| Stage | Skills |
| --- | --- |
| Discover | `vd:scout`, `vd:graphify`, `vd:research`, `vd:brainstorm` |
| Plan | `vd:plan`, `vd:plan-audit`, `vd:scenario` |
| Execute | `vd:cook`, `vd:fix`, `vd:debug`, `vd:codex-workflow` |
| Review and ship | `vd:code-review`, `vd:code-refactor-review`, `vd:simplify`, `vd:zero-tech-debt`, `vd:security`, `vd:ship`, `vd:git` |
| Iterate | `vd:auto-loop`, `vd:optimize-loop` |
| Orchestrate | `vd:ultracook` |

## Agent And Tooling Skills

| Area | Skills |
| --- | --- |
| Browser automation and e2e | `vd:ego-browser`, `vd:browser`, `vd:browser-profile`, `vd:browser-trace`, `vd:agent-browser`, `vd:web-e2e`, `vd:web-perf` |
| Web and frontend | `vd:uiuxdesign`, `vd:opendesign`, `vd:fastreact` |
| CLI engineering and operations | `vd:braze`, `vd:cli-ts`, `vd:smartsheet`, `vd:voice-agent` |
| Docs and diagrams | `vd:docs`, `vd:tech-docs`, `vd:diagram`, `vd:text-diagram`, `vd:excalidraw`, `vd:tldraw-offline` |
| Media, files, and social | `vd:omnimedia`, `vd:marketing-design`, `vd:copywriting`, `vd:show-off`, `vd:file-browser`, `vd:twitter`, `vd:devlog` |
| Design | `vd:apidesign`, `vd:dbdesign` |
| Data and workspace | `vd:miudb`, `vd:vd-cli`, `vd:superwhisper-cli`, `vd:aws`, `vd:cnpg`, `vd:astro-airflow`, `vd:gws`, `vd:jira` |
| Local operations | `vd:computer-clean`, `vd:worktree`, `vd:herd-worktree`, `vd:herdr`, `vd:gopass`, `vd:journal`, `vd:cktovd`, `vd:workbench` |
| Skill lifecycle | `vd:skill-creator`, `vd:skill-management`, `vd:skill-audit`, `vd:rule-miner`, `vd:skill-evolve` |

Within the skill lifecycle, `vd:skill-creator` authors a brand-new skill (description routing, hard rules, verification); `vd:skill-management --create` delegates to it where the runtime supports invoking another skill (Claude Code) and otherwise falls back to the `scripts/new-skill.sh` scaffold, and `vd:skill-management` owns the surrounding mechanics - scaffolding, vendoring via `vd`, frontmatter validation, and releases. `vd:skill-evolve` improves skills that already exist from the current session, `vd:skill-audit` reports which skills actually get used, and `vd:rule-miner` distils repeated corrections into `CLAUDE.md` rules.

Inside Herdr, `vd:worktree` delegates current-pane naming to `vd:herdr` after a successful create, using a short `<project>:<intent>` label.

Within browser automation, `vd:ego-browser` drives logged-in browsing through isolated ego lite task spaces, follows the active app's embedded runtime contract, and asks before closing each completed space so short tasks do not leave clutter behind. `vd:agent-browser` is the direct CDP driver for the persistent Chrome that `vd:browser-profile` launches, and keeps its own video-recording and network-mocking specialties. `vd:browser-trace` captures vendor-free raw-CDP traces (console, network, lifecycle) against that same local Chrome. `vd:browser` is scoped to Browserbase cloud sessions only - the escalation target for CAPTCHA, anti-bot, and proxy work when a local run hits a wall. `vd:web-e2e` orchestrates logged-in end-to-end flows on top of them.

`vd:jira` uses the `vanducng/jira-cli` fork for native inline local-image comments, accepts `--project` and `--type bug|task` for untracked local rules, and maps board columns to verified workflow transitions.

## Language And Migration

`vd:cli-ts` guides production TypeScript CLI architecture, agent-friendly contracts, npm packaging, CI/CD, documentation, and trusted publishing without replacing a repository's working stack unnecessarily.

`vd:golang` consolidates idiomatic Go guidance - style and naming, error handling and safety, concurrency and performance, testing and CI, project layout and dependencies, and observability and gRPC - routing by topic to `skills/golang/references/`. `vd:gostack` is an opinionated reference for Sam Berthe's Go libraries (`lo`, `oops`, `do`, `mo`, `slog`, `hot`, `ro`), with per-library notes under `skills/gostack/references/`. `vd:py2go` runs end-to-end Python-to-Go migrations with six project-type playbooks and pinned stack defaults.

## Infrastructure And Deployment

`vd:aws` operates AWS accounts and services through the official CLI with identity-first scoping, cross-service incident tracing, focused references for serverless, compute/networking, observability/storage, explicit mutation boundaries, and a gopass-backed `reset-password` workflow.

`vd:devops` covers deployment and infrastructure operations - Docker and Docker Compose, Kubernetes (`kubectl`, Helm, RBAC), Terraform/OpenTofu, cloud platforms (GKE/EKS, Cloud Run, Cloudflare Workers/R2/D1), GitHub Actions CI/CD, and GitOps (Argo CD, Flux) - with per-topic notes under `skills/devops/references/`.

## Choosing The Right Skill

Use `vd:scout` when you need a map, `vd:debug` when behavior is failing, `vd:plan` when the implementation path is not yet concrete, `vd:cook` when a plan is ready to execute, and `vd:ship` when the work is tested and ready for remote.

Within review, the four passes answer different questions: `vd:code-review` asks whether a change is ready to land and posts inline PR comments, `vd:code-refactor-review` stays local and asks whether the change fits the codebase or reads as slop, `vd:simplify` reduces reading complexity with behavior frozen, and `vd:zero-tech-debt` reshapes a working feature into the form it should have had from day one, deleting compatibility paths only after proving them dead.

Use `vd:docs` for canonical internal project docs and ADRs. Use `vd:tech-docs` to create, modernize, validate, and ship a rendered public developer documentation site.

Use `vd:superwhisper-cli` to search local dictation history, prepare standups or commitment reviews, diagnose raw versus processed transcription errors, and maintain vocabulary or snippets with approval.

Use `vd:braze` for category-first Braze reads, leaf-permission diagnosis, explicit opt-in or opt-out changes, and end-to-end `braze-cli` validation.

Use `vd:smartsheet` to discover and read sheets with bounded JSON commands, then perform only explicitly authorized row additions or updates with read-back verification.

Use `vd:voice-agent` to operate Retell through `vac` with bounded reads, explicit write authorization, current endpoint guidance, and structured recovery.

Use `vd:tldraw-offline` to inspect, edit, persist, and verify canvases in the local tldraw desktop app. New canvases default to the injected feature visuals directory, with structural, persistence, and conditional visual completion gates.
