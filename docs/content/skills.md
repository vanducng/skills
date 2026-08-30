---
title: "Skills"
---

The catalog currently contains 79 skills under `skills/`. Each skill is self-contained and starts with a `SKILL.md` file. Optional scripts, references, and assets live inside the same skill directory.

Source: `find skills -mindepth 1 -maxdepth 1 -type d`, `scripts/validate.sh`.

`vd:guide` is the catalog front door when several skills could apply. The ask-to-ship path is on [Getting Started](/getting-started/#from-ask-to-ship).

## Core Delivery Flow

| Stage | Skills |
| --- | --- |
| Route | `vd:guide` |
| Define | `vd:interview` (`--grill`, `--wayfinder`) |
| Discover | `vd:scout`, `vd:graphify`, `vd:research` |
| Decide | `vd:brainstorm` |
| Plan | `vd:plan` (`--audit`), `vd:scenario` |
| Execute | `vd:cook`, `vd:fix`, `vd:debug`, `vd:codex-workflow` |
| Review and ship | `vd:code-review` (`--refactor`), `vd:miucr`, `vd:simplify` (`--aggressive`), `vd:security`, `vd:ship`, `vd:git` |
| Iterate | `vd:auto-loop`, `vd:optimize-loop` |
| Orchestrate | `vd:ultracook` |

`vd:interview` is the alignment skill: default extracts want, `--grill` walks an existing plan or idea (the grilling primitive other skills compose), `--wayfinder` charts a multi-session map of decision tickets. One-session deciding after want is confirmed is `vd:brainstorm`. `vd:plan --audit` is the clean-context second look (auto on `--deep`). `vd:ultracook` composes these skills by name with checkable done-when gates; it does not own their discipline.

## Interview And Decision

| Skill | Question |
| --- | --- |
| `vd:interview` | What do you actually want? |
| `vd:interview --grill` | Are these decisions the right ones? |
| `vd:interview --wayfinder` | What must be decided, in what order, across sessions? |
| `vd:brainstorm` | How should I approach this (3+ options)? |
| `vd:research` | Which known option should I pick? |
| `vd:scenario` | What could break? |

## Review Lenses

| Skill | Question |
| --- | --- |
| `vd:code-review` | Ready to land? (posts on a PR) |
| `vd:code-review --refactor` | Does this fit the codebase, or is it slop? (local) |
| `vd:simplify` | Can this read easier with behavior frozen? |
| `vd:simplify --aggressive` | What shape should this have had from day one? |
| `vd:security` | What can an attacker do? |
| `vd:plan --audit` | Does this plan hold up against the codebase? |
| `vd:miucr` | Deterministic owned reviewer CLI (`miu-cr`) |

## Browser And Web

Escalation ladder (start local; `vd:browser` is the cloud fallback):

| Rung | Skill |
| --- | --- |
| Isolated logged-in browsing | `vd:ego-browser` |
| Persistent local Chrome / CDP | `vd:agent-browser`, `vd:browser-profile` |
| Vendor-free raw-CDP traces | `vd:browser-trace` |
| CAPTCHA / anti-bot / proxy | `vd:browser` (Browserbase) |
| Logged-in end-to-end | `vd:web-e2e` |
| Performance | `vd:web-perf` |

## Design And Media

| Area | Skills |
| --- | --- |
| Web and frontend | `vd:uiuxdesign`, `vd:opendesign`, `vd:fastreact` |
| Interface and storage design | `vd:apidesign`, `vd:dbdesign` |
| Media, files, and social | `vd:omnimedia`, `vd:marketing-design`, `vd:copywriting`, `vd:unslop`, `vd:show-off`, `vd:file-browser`, `vd:twitter`, `vd:devlog` |

## Docs And Diagrams

| Need | Skill |
| --- | --- |
| Canonical internal docs and ADRs; public site via `site` | `vd:docs` |
| ASCII sketch | `vd:text-diagram` |
| General SVG or raster | `vd:diagram` |
| Editable whiteboard | `vd:excalidraw` |
| Polished, accessible HTML/SVG | `vd:diagram-design` |

## Languages And Migration

| Skill | Covers |
| --- | --- |
| `vd:golang` | Idiomatic Go; topic notes under `skills/golang/references/` |
| `vd:gostack` | Sam Berthe's Go libraries (`lo`, `oops`, `do`, `mo`, `slog`, `hot`, `ro`) |
| `vd:py2go` | Python-to-Go migrations with six project-type playbooks |
| `vd:cli-ts` | Production TypeScript CLI architecture and packaging |

## Infra And Ops

| Skill | Covers |
| --- | --- |
| `vd:devops` | Docker, Kubernetes, Terraform/OpenTofu, cloud platforms, GitHub Actions, GitOps; deploy-verify checks for image/rollout/CI |
| `vd:aws` | Official AWS CLI, identity-first scoping, incident tracing |
| `vd:cnpg` | CloudNativePG operations |
| `vd:astro-airflow` | Remote Astro / Airflow inspection (`af`, deployment logs) |
| `vd:dag-factory` | YAML DAG authoring (map vs list dialect) |
| `vd:managing-astro-local-env` | Local `astro dev` lifecycle |
| `vd:delegating-to-otto` | Headless `astro otto` |

## Product CLIs

Owned CLIs documented as manuals (not generic "how to review/code"):

| Skill | Product |
| --- | --- |
| `vd:miucr` | `miu-cr` deterministic reviewer |
| `vd:miudb` | `miudb` |
| `vd:vd-cli` | `vd` catalog/install CLI |

## Personal Ops

Daily-driver utilities, categorized honestly:

`vd:superwhisper`, `vd:gws`, `vd:jira`, `vd:issue-invoice`, `vd:computer-clean`, `vd:worktree`, `vd:herd-worktree`, `vd:herdr`, `vd:gopass`, `vd:journal`, `vd:workbench`, `vd:braze`, `vd:smartsheet`, `vd:voice-agent`

## Skill Lifecycle

| Skill | Owns |
| --- | --- |
| `vd:skill-creator` | Authoring a new `SKILL.md` (description, hard rules, writing principles) |
| `vd:skill-management` | Scaffold, vendor, validate, release (`--create` delegates authoring) |
| `vd:skill-evolve` | Improve skills that already exist |
| `vd:skill-audit` | Which skills actually get used |
| `vd:rule-miner` | Distil repeated corrections into `CLAUDE.md` rules |
| `vd:agent-readiness` | Score a repo against a 30-signal rubric and remediate |

## Choosing The Right Skill

Use `vd:guide` when the next skill is unclear. Use `vd:interview` when the ask is underspecified, `vd:interview --grill` when a plan or idea needs its decisions walked, `vd:interview --wayfinder` when the deciding itself will not fit one session, `vd:scout` when you need a map of the repo, `vd:debug` when behavior is failing, `vd:brainstorm` when the outcome is known but the one-session approach is not, `vd:plan` when the implementation path is not yet concrete, `vd:cook` when a plan is ready to execute, `vd:git` for a single commit/push/PR/merge (`gh pr checks` exit 8 is pending, not failure), and `vd:ship` when the work is tested and ready for remote.

Within review: `vd:code-review` asks whether a change is ready to land and posts inline PR comments; `vd:code-review --refactor` stays local and asks whether the change fits the codebase; `vd:simplify` reduces reading complexity with behavior frozen; `vd:simplify --aggressive` reshapes a working feature into the form it should have had from day one, deleting compatibility paths only after proving them dead. `vd:miucr` is the deterministic owned reviewer CLI for when the review itself must be reproducible.

Use `vd:docs` for canonical internal project docs and ADRs, and its `site` subcommand to create, modernize, validate, and ship a rendered public developer documentation site.

Use `vd:diagram-design` for polished, accessible, self-contained HTML/SVG diagrams. Use `vd:text-diagram` for ASCII sketches, `vd:diagram` for general SVG or raster output, and `vd:excalidraw` for editable whiteboard canvases.

Use `vd:superwhisper` to search local dictation history, prepare standups, and diagnose recognition errors. Use `vd:braze` for Braze CLI reads and explicit opt-in changes. Use `vd:smartsheet` for bounded sheet reads and authorized row updates. Use `vd:voice-agent` to operate Retell through `vac`.

`vd:jira` uses the `vanducng/jira-cli` fork for native inline local-image comments. Inside Herdr, `vd:worktree` delegates current-pane naming to `vd:herdr` after a successful create. `vd:worktree` also trusts and installs mise tools when a mise config is present. `vd:computer-clean` also audits Git worktree storage.

A lingering `.ck.json` without `.vd.json` is a rename (`mv .ck.json .vd.json`), not a skill.
