---
title: "Skills"
---

The catalog contains 83 skills under `skills/`. Each one starts with `SKILL.md`; any scripts, references, and assets stay in that directory. Claude Code, Codex, and Pi all install from this catalog.

Count source: `find skills -mindepth 1 -maxdepth 1 -type d`. Validation: `scripts/validate.sh`.

Use `vd:guide` when several skills fit. The full delivery path is on [Getting started](/getting-started/#from-ask-to-ship).

## Core delivery flow

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

`vd:interview` confirms the outcome and constraints. `--grill` tests an existing plan or idea. `--wayfinder` maps decisions that will take more than one session. After the outcome is clear, use `vd:brainstorm` to choose an approach. Use `vd:plan --audit` for an independent plan check; `--deep` runs it automatically. `vd:ultracook` chains these skills with explicit completion checks.

## Interview and decision

| Skill | Question |
| --- | --- |
| `vd:interview` | What do you actually want? |
| `vd:interview --grill` | Are these decisions the right ones? |
| `vd:interview --wayfinder` | What must be decided, in what order, across sessions? |
| `vd:brainstorm` | How should I approach this (3+ options)? |
| `vd:research` | Which known option should I pick? |
| `vd:scenario` | What could break? |

## Review lenses

| Skill | Question |
| --- | --- |
| `vd:code-review` | Ready to land? (posts on a PR) |
| `vd:code-review --refactor` | Does this fit the codebase, or is it slop? (local) |
| `vd:simplify` | Can this read easier with behavior frozen? |
| `vd:simplify --aggressive` | What shape should this have had from day one? |
| `vd:security` | What can an attacker do? |
| `vd:plan --audit` | Does this plan hold up against the codebase? |
| `vd:miucr` | Deterministic owned reviewer CLI (`miu-cr`) |

## Browser and web

Start with a local browser. Use `vd:browser` only when the site blocks local automation:

| Rung | Skill |
| --- | --- |
| Isolated logged-in browsing | `vd:ego-browser` |
| Persistent local Chrome / CDP | `vd:agent-browser`, `vd:browser-profile` |
| Vendor-free raw-CDP traces | `vd:browser-trace` |
| CAPTCHA / anti-bot / proxy | `vd:browser` (Browserbase) |
| Logged-in end-to-end | `vd:web-e2e` |
| Performance | `vd:web-perf` |

## Design and media

| Area | Skills |
| --- | --- |
| Web and frontend | `vd:uiuxdesign`, `vd:opendesign`, `vd:fastreact` |
| Interface and storage design | `vd:apidesign`, `vd:dbdesign` |
| Media, files, and social | `vd:omnimedia`, `vd:marketing-design`, `vd:copywriting`, `vd:unslop`, `vd:show-off`, `vd:file-browser`, `vd:twitter`, `vd:devlog` |

## Docs and diagrams

| Need | Skill |
| --- | --- |
| Canonical internal docs and ADRs; public site via `site` | `vd:docs` |
| Cheap in-chat visual for the current topic | `vd:show-me` |
| ASCII sketch | `vd:text-diagram` |
| General SVG or raster | `vd:diagram` |
| Editable whiteboard | `vd:excalidraw` |
| Polished, accessible HTML/SVG | `vd:diagram-design` |

## Languages and migration

| Skill | Covers |
| --- | --- |
| `vd:golang` | Idiomatic Go; topic notes under `skills/golang/references/` |
| `vd:gostack` | Sam Berthe's Go libraries (`lo`, `oops`, `do`, `mo`, `slog`, `hot`, `ro`) |
| `vd:py2go` | Python-to-Go migrations with six project-type playbooks |
| `vd:cli-ts` | Production TypeScript CLI architecture and packaging |

## Infra and ops

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

These skills document CLIs owned alongside this catalog:

| Skill | Product |
| --- | --- |
| `vd:miucr` | `miu-cr` deterministic reviewer |
| `vd:miudb` | `miudb` |
| `vd:vd-cli` | `vd` catalog/install CLI |

## Personal ops

Utilities for recurring work:

`vd:superwhisper`, `vd:gog`, `vd:jira`, `vd:kaneo`, `vd:issue-invoice`, `vd:computer-clean`, `vd:worktree`, `vd:herd-worktree`, `vd:herdr`, `vd:gopass`, `vd:onepassword`, `vd:journal`, `vd:workbench`, `vd:braze`, `vd:smartsheet`, `vd:voice-agent`, `vd:alter`

## Skill lifecycle

| Skill | Owns |
| --- | --- |
| `vd:skill-creator` | Authoring a new `SKILL.md` (description, hard rules, writing principles) |
| `vd:skill-management` | Scaffold, vendor, validate, release (`--create` delegates authoring) |
| `vd:skill-evolve` | Improve skills that already exist |
| `vd:skill-audit` | Which skills actually get used |
| `vd:rule-miner` | Distil repeated corrections into `CLAUDE.md` rules |
| `vd:agent-readiness` | Score a repo against a 30-signal rubric and remediate |

## Choosing the right skill

Use `vd:guide` when the next step is unclear. Use `vd:interview` for an underspecified request, `--grill` to test an existing idea, and `--wayfinder` to map decisions across sessions. Use `vd:scout` to map the repository and `vd:debug` to trace a failure. Once the outcome is clear, use `vd:brainstorm`, then `vd:plan` and `vd:cook` as needed. `vd:git` handles one commit, push, PR, or merge; exit 8 from `gh pr checks` means checks are pending. Use `vd:ship` when tested work is ready for a remote branch and PR.

For reviews, `vd:code-review` posts PR findings and `vd:code-review --refactor` stays local. `vd:simplify` reduces complexity without changing behavior. `--aggressive` may remove compatibility paths after proving they are dead. Use `vd:miucr` when the review must be reproducible.

Use `vd:docs` for internal project docs and ADRs. Its `site` subcommand manages a public documentation site.

Use `vd:show-me` for a quick in-chat visual. Use `vd:diagram-design` for accessible HTML/SVG, `vd:text-diagram` for ASCII, `vd:diagram` for SVG or raster output, and `vd:excalidraw` for editable whiteboards.

Use `vd:superwhisper` to search local dictation history, prepare standups, and diagnose recognition errors. Use `vd:alter` to audit Alter's macOS global hotkeys and change them without reading meeting data. Use `vd:braze` for Braze CLI reads and explicit opt-in changes. Use `vd:smartsheet` for bounded sheet reads and authorized row updates. Use `vd:voice-agent` to operate Retell through `vac`. Use `vd:gopass` for the local GPG password store and `vd:onepassword` for 1Password CLI (`op` / `op://` references).

`vd:kaneo` manages Kaneo tickets through REST or MCP; instance values live in `$HOME/.config/vd/kaneo-rules/`. `vd:jira` uses the `vanducng/jira-cli` fork for inline local-image comments. Inside Herdr, `vd:worktree` asks `vd:herdr` to name the current pane after creating a worktree. It also trusts mise configs so `cd` works, while `mise install` stays in `suggestedInstalls`. `vd:computer-clean` checks Git worktree storage.

A lingering `.ck.json` without `.vd.json` is a rename (`mv .ck.json .vd.json`), not a skill.
