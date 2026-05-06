# vd Usage Guide

`vd` manages skills in this repository from source import through local agent installation. Use this page as the quick operational guide; see [commands.md](commands.md) for full flag-level reference.

![vd CLI feature overview](vd-cli-overview.svg)

## Core Workflow

Start by creating a manifest, registering skills, syncing them to disk, and building local agent targets:

```sh
vd init
vd add browserbase/skills/browser --as browser
vd sync
vd build
```

`vd init` creates `skills.toml`. `vd add` records an upstream skill source. `vd sync` vendors tracked skills into `skills/<name>/`, updates `skills.lock`, and runs `vd build` unless `--no-build` is set. `vd build` regenerates Claude plugin metadata and repo-scoped Codex symlinks.

## Main Features

| Feature | Commands | Purpose |
|---|---|---|
| Manifest setup | `vd init` | Create or refresh `skills.toml` from repository defaults. |
| Upstream tracking | `vd add`, `vd sync`, `vd update` | Register skills, vendor them locally, and move tracked skills to upstream HEAD. |
| Version control | `vd pin`, `vd detach`, `vd remove` | Freeze a skill at a SHA, stop tracking it, or remove it cleanly. |
| Inspection | `vd list`, `vd diff`, `vd doctor` | Review tracked skills, compare local edits, and detect drift from `skills.lock`. |
| Target builds | `vd build claude`, `vd build agents` | Generate `.claude-plugin/` files and `.agents/skills/` symlinks. |
| Agent install | `vd install codex`, `vd install claude` | Install local skills into Codex or Claude Code. |
| Cache control | `vd cache clean` | Remove `.vd-cache/` and force future fetches to repopulate it. |

## Common Commands

```sh
vd list                         # show manifest skills and lock SHAs
vd doctor                       # report modified, missing, or untracked skill dirs
vd diff research                # compare cached upstream vs skills/research/
vd update                       # update all tracked skills
vd pin browser abc1234          # pin browser to a specific commit
vd detach research              # keep files but stop upstream tracking
vd remove browser --keep-files  # untrack without deleting files
vd cache clean                  # remove the repo download cache
```

Use `--root <path>` or `VD_ROOT=/path/to/repo` when running `vd` outside the repository. Set `VD_NO_UPDATE_CHECK=1` to disable release checks.

## Installing Into Agents

Codex installs use symlinks by default so local edits in `skills/<name>/` are visible after restarting Codex:

```sh
vd install codex                    # symlink all skills to $HOME/.agents/skills
vd install codex research plan      # install selected skills
vd install codex --scope repo       # symlink into .agents/skills for this repo
vd install codex --copy --force     # replace existing entries with copied snapshots
vd install                          # open the TUI picker for agent/install mode
```

Claude Code installs build the plugin bundle, register this repository as a marketplace, and install the configured plugin:

```sh
vd install claude
vd install claude --dry-run
```

## Safe Update Pattern

Before pulling upstream changes, check local state:

```sh
vd doctor
vd diff <skill>
vd update <skill>
```

`vd sync` and `vd update` refuse to overwrite locally modified skills unless `--force` is passed. Use `vd detach <skill>` when a skill should become locally maintained.
