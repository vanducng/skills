---
name: workbench
description: "Resolve where a unit of work keeps its records (SPEC.md, PROGRESS.md, PROOF.md, reports/) - the slice folder in an OpenRig rig, .workbench/<id>/ elsewhere. Creates and checks a bench folder, attaches proof without a rig, migrates old features trees. Use when asked where to write a report, proof or progress note, to start a record, or to migrate the workbench."
license: MIT
metadata:
  author: vanducng
  version: "0.2.0"
---

# Workbench

One record shape, in one of two places: `SPEC.md`, `PROGRESS.md`, `PROOF.md`, `reports/`, `proof/`. Ask the resolver where; never build the path yourself.

```bash
R=<this skill's directory>/scripts/records.cjs   # next to this SKILL.md
node "$R" resolve --json
```

`resolve` prints `mode`, `dir`, `spec`, `progress`, `proofFile`, `proofDir`, `reports` and `proofAdd`. Notes, reviews and reports go in `reports`.

## In a rig

`mode: rig` when `OPENRIG_SESSION_NAME` is set (no `workspace.yaml` via `--root`, `$PROJECTS_ROOT` or the cwd: exit 2). `dir` is the slice folder, found from `--slice <NN-slug|mission/NN-slug|path>`, a worktree named `<repo>-<code>-s<nn>`, or the cwd. If the slice cannot be named, `resolve` exits 2: pass `--slice`. It never falls back to `.workbench/`, so a rig has one record.

Evidence goes in with the printed `proofAdd` plus `--artifact-type guard|qa|rev1-r1|rev1-r2|adjudication --verdict CLEAR|BLOCKING|CONCERNING|PASS|NOT-CLEAR`, `--candidate-sha`, `--money-evidence` and `--file`. Do not write `PROOF.md` or `proof/` by hand. Slice folders come from `rig scope slice create`; `init` refuses in a rig.

## Outside a rig

`mode: bench`. The record is `<main worktree>/.workbench/<id>/{SPEC.md,PROGRESS.md,PROOF.md,proof/,reports/}`; the id is `--id`, else the branch (`feat/PROJ-12-x` gives `proj-12-x`).

| Command | Does |
|---|---|
| `init [--id I] [--intent T]` | Create the folder from the templates. Idempotent; never overwrites. |
| `check <dir> [--stage close]` | The `rig scope audit` rules: authored intent, numbered mini-requirements, checkbox proof contract, valid proof headers; at close, the retro line. Exit 1 on findings. |
| `proof add <dir> --artifact-type T --verdict V --candidate-sha S --money-evidence M (--file F \| --body B)` | Write `proof/<name>.md` with the same C1 header as `rig proof add` and list it in `PROOF.md`. Optional `--evidences`, `--self-check`, `--media`, `--name`, `--replace`. |

A fresh `init` folder fails `check` until its `TODO` lines are authored. Captures stay under `~/.share/openrig/`, cited by sha256.

## Migrating old trees

`migrate` lists what it would move from `.workbench/features/<id>/`; `migrate --apply` moves it to `.workbench/<id>/` (`reports/` as is; plans, visuals, journals and state under `reports/<type>/`; `feature.json` kept in `reports/`; a `SPEC.md` written from its label). It never overwrites: a name clash is reported and left. A second run does nothing. Run it only after the hook layout change lands, or old producer skills recreate `features/`.

## Old commands

`scripts/workbench.py new <slug>` calls `init --id <slug>`; it refuses `--ticket` and `--parent`. Every other old command prints "removed" and exits 2. `feature.json`, `INDEX.md` and the five type folders are gone.

## Notes

Producer skills that write to the hook-injected `Reports:` path keep doing so; that path changes with the hook layout, not here. Bench folders sit under the main worktree, so they outlive `git worktree remove`.
