---
name: docs
description: "Manage project documentation in ./docs/ — initialize, update, check, or record an ADR (architecture decision record). Canonical set is intentionally small: development guidelines, system architecture, tech stack, deployment; plus append-only decision history under docs/decisions/. Scouts the codebase, delegates writing to the docs-manager subagent (or stays inline with --inline)."
license: MIT
argument-hint: "init|update|check|adr [topic] [--inline] [--dry-run]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Docs

Keep `./docs/` honest. Scout the code, diff it against what the docs claim, write what's true. Small canonical set — easy to keep current, hard to let rot.

## What this skill is — and isn't

| Skill | Question it answers | Output |
|---|---|---|
| `vd:scout` | "Where does X live in this repo?" | File map, no writes |
| `vd:journal` | "What did *I* just learn / decide / break?" | Personal entry in `.work/journals/` or `plans/journals/` |
| **`vd:docs`** | **"Are the shared `./docs/` files true and current?"** | **Updated files in `./docs/`** |

`./docs/` is **team-facing** truth. Journals are personal. Plans/reports live under `./plans/`. Changelog, roadmap, and PR-style narrative are intentionally **not** in this skill's scope — those rot fastest and `vd:ship` / `vd:journal` already cover them.

## Subcommands

| Subcommand | Reference | When |
|---|---|---|
| `init` | `references/init-workflow.md` | Fresh repo — no `./docs/` yet, or only a stub README |
| `update` | `references/update-workflow.md` | Code drifted from docs after a feature, refactor, or migration |
| `check` | `references/check-workflow.md` | Validate-only: required files, size, freshness, broken refs. No writes. |
| `adr` | `references/adr-workflow.md` | Record an architecture decision (the *why* behind an irreversible choice) under `docs/decisions/` |

Parse `$ARGUMENTS` first word:
- `init` / `update` / `check` / `adr` → load the matching reference
- empty / unclear → `AskUserQuestion` with the options. Don't auto-run `init` — it writes files.

## Flags

| Flag | Effect |
|---|---|
| `--inline` | Skip `docs-manager` subagent — write from main context. Use when you want to drive the writing yourself or the subagent is unavailable. |
| `--dry-run` | Print the plan (files to scan, files to write/touch) and stop. No subagent, no writes. Use before letting a subagent churn on a large repo. |

## Canonical doc set

Intentionally short. Every file here earns its place — code-derivable, frequently consulted, and stable enough not to need weekly rewriting.

| File | Purpose | Required? |
|---|---|---|
| `README.md` | Project entry point, ≤ 300 lines — what is this, how to run it, where to read more | Yes |
| `docs/development-guidelines.md` | Code style, naming conventions, file layout, local dev setup, contribution flow | Yes |
| `docs/system-architecture.md` | Components, data flow, integrations, module boundaries | Yes |
| `docs/tech-stack.md` | Languages, frameworks, runtimes, key libraries, infra services — what powers this | Yes |
| `docs/deployment.md` | CI/CD pipelines, environments, deploy steps, env vars, rollback procedure | Yes |

**Out of scope** (by design):
- Changelog → `vd:ship` writes `CHANGELOG.md` directly
- Project roadmap → lives in plans (`./plans/`) or your issue tracker, not here
- Codebase summary → `vd:scout` produces this on demand; doesn't need a static file
- PRD / requirements → product artifact, not a code-derivable doc

If a project has good reasons to maintain those, add them outside `vd:docs`'s automated touch — this skill won't read, write, or validate them.

**`docs/decisions/` (ADRs) is a special case** — append-only decision history written by the `adr` subcommand, not current-state docs. It is **exempt from freshness, size-budget, and citation validation**: an old ADR is *correct* (it records what was decided then), and a superseded one stays in place with its status flipped. `check` must skip `docs/decisions/`.

## Pre-flight: missing `./docs/`

Before any subcommand except `init`:

1. If `./docs/` does not exist → ask the user: run `init` now, or abort?
2. If `./docs/` exists but is empty → same question.
3. If a single required file is missing → flag it in the plan; create it as part of the run.

Never create `./docs/` silently. The user owns this directory.

## Writer strategy

| Condition | Writer |
|---|---|
| Default, `docs-manager` subagent available | Delegate via `Agent` tool — passes the scout digest + doc readings, returns when files are written |
| `--inline`, or subagent unavailable | Write from main context using the reference workflow's checklist |
| `check` | Always inline — no writes |

When delegating, pass: scout digest, current doc LOC table, the user's `$ARGUMENTS`, plan dir (if any). Do **not** pass full file contents — let the subagent re-read what it needs.

After `init` or `update` writes files, list every changed doc with an openable location:
`[deployment.md](/absolute/path/to/docs/deployment.md)` and, when helpful,
`file:///absolute/path/to/docs/deployment.md`. Repo-relative paths are fine as
secondary context, but never hand off only a basename.

## Token efficiency

- **Scout in parallel, write once.** Don't re-scout per doc file.
- **Read docs in bulk when many.** If `ls docs/*.md | wc -l` ≥ 4, spawn `Explore` subagents to read in parallel — see `references/update-workflow.md` Phase 1.5.
- **Don't dump full `git diff` into the subagent prompt** — `git log --oneline` + `git diff --stat` is enough; the subagent pulls scoped diffs only for files it names.
- **`--dry-run` costs almost nothing** — run it first on unfamiliar repos.

## Quality bar

- **Every claim has a citation.** Architecture docs name the file path. Tech-stack entries name the version (from lockfile / `package.json` / `go.mod`). No "the system uses XYZ" without `src/...:N`.
- **No filler.** If a section in a template has nothing concrete, delete it — don't pad with "TBD".
- **Size budget.** `docs.maxLoc` from session context (default 800). Over budget → split or trim, not "accept as-is".
- **Validation runs after every write.** `references/update-workflow.md` Phase 4 — non-blocking, but report what it finds.

## Workflow position

**Typically follows:** `vd:ship` (after the PR lands, sync `./docs/` to the new reality), `vd:cook` (end of plan), major refactor or migration.

**Typically precedes:** Nothing — `vd:docs` is terminal. Next pipeline starts at `vd:scout` or `vd:plan`.

**Do not** run `vd:docs` mid-implementation — docs drift faster than code does. Wait until the code is stable.

## Hard rules

1. **Never write outside `./docs/` or `./README.md`.** Plans, journals, and reports have their own homes.
2. **Never invent.** If the scout digest doesn't support a claim, the docs don't make it.
3. **Never run `init` on a populated `./docs/`.** `update` is the right verb — `init` is for empty trees.
4. **`--dry-run` before any big sync.** Especially on repos you don't own well.
5. **One file write per doc.** No append-mode, no patch-on-patch. Subagent rewrites the file in full or not at all.
