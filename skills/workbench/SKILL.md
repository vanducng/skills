---
name: workbench
description: Manage the feature-first .workbench umbrella — create, resolve, switch, list, archive, and gc per-feature folders ({ticket}-{slug}) that group plans/reports/visuals/journals/state. Use when the user says "workbench new", "list features", "archive feature", "switch feature", "what feature am I on", "clean up .workbench", or needs to organize agent artifacts under .workbench/features/.
---

# Workbench

Lifecycle owner for the **feature-first** `.workbench/` umbrella. One folder per feature — `features/{ticket}-{slug}/{plans,reports,visuals,journals,state}/` — so a ticket's artifacts stay together instead of scattering across type-first sibling dirs.

This skill owns the **write path** (create / archive / gc). The control-plane hooks own read-path resolution, so `workbench new` computes the exact id the hooks resolve — they never diverge (it reuses `~/.claude/hooks/lib`).

## Prerequisites

- The repo opts into feature-first: `paths.umbrella` set and `paths.layout: "feature-first"` in `<git-root>/.vd.json`.
- Hooks deployed (`vd install hooks`). Without them the CLI errors with a clear message.
- A type-first repo can still be inspected, but feature routing only activates under `feature-first`.

## Run

```bash
node ~/.claude/skills/workbench/scripts/workbench.cjs <command> [args]
```

| Command | Does |
|---|---|
| `new [slug] [--ticket T] [--parent id] [--from-scratch]` | Create (or switch to) a feature folder. Idempotent: an existing ticket/slug switches instead of duplicating. With no args, derives `{ticket}-{slug}` from the current `feat/*` branch. `--from-scratch` promotes `_global/scratch/` content. |
| `resolve [--json]` | Print the resolved feature + all five type-paths for the current context — the author verify-loop. |
| `switch <id\|ticket\|slug>` | Set this session's active feature (per-session, via `VD_SESSION_ID`). The cross-session / multi-ticket escape hatch. |
| `list [--status active\|done\|archived\|all]` | Table of features, derived by scanning `feature.json` (reconciled against disk). |
| `status [id]` | Detail for one feature: ticket, status, artifact counts, supersede chain, relatedDocs. |
| `archive <id> [--reason r] [--superseded-by id]` | Move `features/<id>` → `_archive/<id>` and mark `status: done`. |
| `restore <id>` | Move `_archive/<id>` back to `features/<id>`. |
| `reindex` | Rebuild `.workbench/INDEX.md` from a `feature.json` scan (recovery / human overview). |
| `gc [--force]` | Sweep `tmp/`, `*.pid`, `*.log`. Dry-run by default; `--force` deletes. |
| `triage` | List `_unsorted/` items awaiting a home. |
| `migrate [...]` | Pointer to the native `vd migrate` migrator. |

## Identity

A feature's id is `{ticket}-{slug}` (or `{slug}` when ticketless), **frozen at creation, no date** — the immutable cross-reference for commits/journals/PRs. The human-facing `label` in `feature.json` is renameable; the dir name is not. Resolution is branch-first and deterministic; on a `feat/ELT-3316-...` branch the hooks and this CLI both resolve `elt-3316-...`.

## Notes

- `feature.json` is authoritative; `INDEX.md` and `list` output are derived and rebuildable — they survive `git clean` / machine moves as long as the folders do.
- Reserved roots (`features/`, `_global/`, `_archive/`, `_unsorted/`, `tmp/`) sort apart and can't collide with a feature id.
- Per-type subfolders are fixed (`plans reports visuals journals state`); use `state/` for unmodeled overflow rather than inventing a sixth type.

## Workflow position

**Pairs with:** the producer skills (`vd:scout`, `vd:plan`, `vd:debug`, `vd:journal`, …) which write into the injected paths this resolves. **Follows:** `vd migrate` (one-time migration of an existing umbrella to feature-first).
