---
title: "Skills"
---

The catalog currently contains 66 skills under `skills/`. Each skill is self-contained and starts with a `SKILL.md` file. Optional scripts, references, and assets live inside the same skill directory.

Source: `find skills -mindepth 1 -maxdepth 1 -type d`, `scripts/validate.sh`.

## Core Delivery Flow

| Stage | Skills |
| --- | --- |
| Discover | `vd:scout`, `vd:graphify`, `vd:research`, `vd:brainstorm` |
| Plan | `vd:plan`, `vd:plan-audit`, `vd:scenario` |
| Execute | `vd:cook`, `vd:fix`, `vd:debug`, `vd:codex-workflow` |
| Review and ship | `vd:code-review`, `vd:simplify`, `vd:security`, `vd:ship`, `vd:git` |
| Iterate | `vd:auto-loop`, `vd:optimize-loop` |
| Orchestrate | `vd:ultracook` |

## Agent And Tooling Skills

| Area | Skills |
| --- | --- |
| Browser automation and e2e | `vd:browser`, `vd:browser-profile`, `vd:browser-trace`, `vd:agent-browser`, `vd:web-e2e`, `vd:web-perf` |
| Web and frontend | `vd:uiuxdesign`, `vd:opendesign`, `vd:fastreact` |
| Docs and diagrams | `vd:docs`, `vd:diagram`, `vd:text-diagram`, `vd:excalidraw`, `vd:tldraw-offline` |
| Media, files, and social | `vd:omnimedia`, `vd:marketing-design`, `vd:copywriting`, `vd:show-off`, `vd:file-browser`, `vd:twitter`, `vd:devlog` |
| Design | `vd:apidesign`, `vd:dbdesign` |
| Data and workspace | `vd:cnb-ds-eda`, `vd:miudb`, `vd:vd-cli`, `vd:cnpg`, `vd:astro-airflow`, `vd:gws`, `vd:jira` |
| Local operations | `vd:computer-clean`, `vd:worktree`, `vd:herd-worktree`, `vd:herdr`, `vd:gopass`, `vd:journal`, `vd:cktovd`, `vd:workbench` |
| Skill lifecycle | `vd:skill-management`, `vd:skill-audit`, `vd:rule-miner`, `vd:skill-evolve` |

`vd:jira` accepts `--project` and `--type bug|task` to apply untracked local rules from `~/.config/vd/jira-rules/`.

## Language And Migration

`vd:golang` consolidates idiomatic Go guidance — style and naming, error handling and safety, concurrency and performance, testing and CI, project layout and dependencies, and observability and gRPC — routing by topic to `skills/golang/references/`. `vd:gostack` is an opinionated reference for Sam Berthe's Go libraries (`lo`, `oops`, `do`, `mo`, `slog`, `hot`, `ro`), with per-library notes under `skills/gostack/references/`. `vd:py2go` runs end-to-end Python-to-Go migrations with six project-type playbooks and pinned stack defaults.

## Infrastructure And Deployment

`vd:devops` covers deployment and infrastructure operations — Docker and Docker Compose, Kubernetes (`kubectl`, Helm, RBAC), Terraform/OpenTofu, cloud platforms (GKE/EKS, Cloud Run, Cloudflare Workers/R2/D1), GitHub Actions CI/CD, and GitOps (Argo CD, Flux) — with per-topic notes under `skills/devops/references/`.

## Choosing The Right Skill

Use `vd:scout` when you need a map, `vd:debug` when behavior is failing, `vd:plan` when the implementation path is not yet concrete, `vd:cook` when a plan is ready to execute, and `vd:ship` when the work is tested and ready for remote.

Use `vd:docs` for canonical project docs in `docs/` and `README.md`.

Use `vd:tldraw-offline` to inspect, edit, persist, and verify canvases in the local tldraw desktop app. New canvases default to the injected feature visuals directory, with structural, persistence, and conditional visual completion gates.
