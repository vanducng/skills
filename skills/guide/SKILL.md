---
name: guide
description: "Router over the vd: skill catalog - maps which skill (or flow of skills) fits the situation, without doing the work itself. Use when the user asks 'which skill should I use', 'what skills are there', 'how do these skills fit together', 'where do I start with this task', or when you're about to pick between overlapping skills (review lenses, browser tools, diagram tools, the get-it-done paths) and want the disambiguation rules."
license: MIT
argument-hint: "[the situation or task to route]"
metadata:
  author: vanducng
  version: "0.1.0"
---

# Guide - the catalog's front door

This skill routes; it never does the work. Read the situation, name the skill (or the flow), state why, and hand off. When two skills could fit, use the disambiguation tables below - they are the tie-breakers the individual descriptions can't carry.

## The delivery flow

The spine for shipping real work. Enter at the first stage whose question you can't already answer; skip stages whose answer you have.

| Stage | Question | Skill |
|---|---|---|
| Discover | "Where does the relevant code live?" | `vd:scout` (or `vd:graphify` for a persistent knowledge graph) |
| Decide | "How should we approach this?" | `vd:brainstorm` (invents options, grills you through the open decisions - Plannotator-first). Options already known → `vd:research` (cited comparison) |
| Plan | "What are the steps?" | `vd:plan` (phased plan + Definition of Done; `--audit` for an independent check; Plannotator intercepts approval where installed) |
| Execute | "Build it." | `vd:cook` (phase loop; `--tdd` composes `vd:tdd`) |
| Review | "Ready to land?" | `vd:code-review` (two axes: spec fidelity + standards) |
| Ship | "Land it." | `vd:ship` (branch → PR → CI green) |
| Record | "What happened?" | `vd:journal` (retro / incident note), `vd:docs` (sync team docs) |

**Conducted end-to-end:** `vd:ultracook "<goal>"` classifies the task and runs only the slice it earns, with gates and resumable state. Reach for it when the user wants the whole flow driven, not when they asked for one stage.

## The three "just get it done" paths

| Situation | Path |
|---|---|
| Small clear task, no diagnosis needed (typo, config tweak, one function) | `vd:cook --quick` - implement + verify + test, no plan ceremony |
| Something is *broken* and the cause is unknown | `vd:debug` (diagnose - repro first, ranked hypotheses) → `vd:fix` (repair end-to-end with a regression guard) |
| "Drive this to done, gate me only when it matters" | `vd:ultracook` - direct mode for trivial, pipeline for real work |

Rule: if the word is *broken/failing/wrong*, route through debug/fix (they enforce root-cause-first). If it's *add/change/build*, cook.

## Review lenses - pick by the question

| Question | Lens |
|---|---|
| "Is this change ready to land?" (public, posts to the PR) | `vd:code-review` |
| "Does this fit the codebase / is it slop?" (local, report-only) | `vd:code-review --refactor` |
| "Can this read easier, behavior unchanged?" | `vd:simplify` |
| "What shape should this have had from day one?" (delete cruft) | `vd:simplify --aggressive` |
| "Where in the codebase is refactoring worth it?" | `vd:simplify --scan` |
| "What can an attacker do with this?" | `vd:security` |
| "Does this plan hold up against the codebase?" | `vd:plan --audit` |
| "Review via the miucr CLI / CI review bot" | `vd:miucr` |

## Interview & decision

- `vd:brainstorm` - path unclear, invent 3+ divergent options, then grill to converge.
- `vd:brainstorm --grill` - the idea exists; sharpen it by interviewing the user (rounds of questions with recommended answers, Plannotator-first).
- `vd:research` - options are known; compare with citations.
- `vd:scenario` - enumerate edge cases across 12 risk dimensions (feeds test selection, not a test runner).
- `vd:tdd` - testing discipline: seams, red-before-green, anti-patterns.

## Browser tools - the escalation ladder

| Need | Skill |
|---|---|
| A persistent logged-in Chrome the agent and human share | `vd:browser-profile` |
| Drive pages: click/fill/snapshot/mock (local CDP) | `vd:agent-browser` |
| Isolated agent browsing spaces (don't fight the user's Chrome) | `vd:ego-browser` |
| CAPTCHA / anti-bot walls → cloud session | `vd:browser` |
| Config-driven logged-in e2e test flows | `vd:web-e2e` |
| Core Web Vitals measurement | `vd:web-perf` |
| A browser run failed - collect raw CDP traces | `vd:browser-trace` |

## Diagrams & visuals - pick by artifact

| Want | Skill |
|---|---|
| Rendered architecture/ER/C4/sequence diagram (image/SVG) | `vd:diagram` |
| ASCII diagram inline in markdown/chat | `vd:text-diagram` |
| Editable whiteboard via Excalidraw MCP | `vd:excalidraw` |
| Polished editable HTML/SVG diagram artifact (architecture, ER, sequence, charts) | `vd:diagram-design` |
| Polished single-file HTML page/mockup/deck | `vd:opendesign` |
| Product UI critique + frontend implementation quality | `vd:uiuxdesign` |
| Brand raster assets (logos, banners, social) | `vd:marketing-design` |
| Demo/launch showcase page | `vd:show-off` |
| Analyze or generate audio/video/image via AI | `vd:omnimedia` |

## Docs - two kinds

- `vd:docs` - the project's internal `./docs/` (+ ADRs behind the three-part gate, optional glossary).
- `vd:tech-docs` - a public Starlight documentation site.

## Loops

- `vd:auto-loop` - grind a goal to verified done (stop-hook loop, two-vote gate). Ultracook's iteration engine.
- `vd:optimize-loop` - improve a *numeric metric* in bounded keep/discard iterations.

## Skill lifecycle

`vd:skill-creator` (author new) → `vd:skill-management` (scaffold/vendor/release) → `vd:skill-evolve` (improve from a session) → `vd:skill-audit` (usage stats) → `vd:rule-miner` (distill corrections into CLAUDE.md rules).

## Everything else

Language guidance (`vd:golang`, `vd:gostack`, `vd:py2go`), infra/ops (`vd:aws`, `vd:devops`, `vd:cnpg`, `vd:astro-airflow`), product CLIs (`vd:miudb`, `vd:vd-cli`), workspace tools (`vd:gws`, `vd:jira`, `vd:smartsheet`, `vd:braze`), parallel isolation (`vd:worktree`, `vd:herdr`, `vd:herd-worktree`), personal ops (`vd:computer-clean`, `vd:issue-invoice`, `vd:resume-screen`, `vd:superwhisper`, `vd:twitter`, `vd:devlog`), and the rest are cataloged with one-line purposes in the repo's `docs/content/skills.md` - route by their own descriptions.

## Output rule

Answer with: the skill (or ordered flow of skills), one sentence on why it fits over the nearest alternative, and the invocation line. Then stop - invoking is the user's (or the calling agent's) move.
