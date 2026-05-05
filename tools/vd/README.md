# vd — Claude skills CLI

A single binary that tracks, vendors, and publishes Claude Code skills inside a Git monorepo.

## Why it exists

- One manifest (`skills.toml`) replaces ad-hoc copy-paste vendoring of upstream skills.
- `vd sync` fetches skills atomically and detects local edits before overwriting.
- `vd build` regenerates `.claude-plugin/marketplace.json` byte-for-byte from the manifest.

## Install

**go install (requires Go 1.23+):**
```sh
go install github.com/vanducng/skills/tools/vd/cmd/vd@latest
```

**Homebrew (tap pending):**
```sh
brew install vanducng/tap/vd
```

**curl installer:**
```sh
curl -fsSL https://raw.githubusercontent.com/vanducng/skills/main/install.sh | sh
```

**Build from source:**
```sh
cd tools/vd
make build          # produces ./vd
mv vd /usr/local/bin/vd
```

## Quick start

```sh
# 1. Create manifest at repo root (reads live marketplace.json for defaults)
vd init

# 2. Add an upstream skill
vd add browserbase/skills/browser --as browser

# 3. Vendor it into skills/
vd sync

# 4. Regenerate .claude-plugin/ (runs automatically after sync, explicit call optional)
vd build
```

After these steps:
- `skills/browser/` contains the vendored skill.
- `.agents/browser` is a symlink (for agent context loading).
- `.claude-plugin/marketplace.json` and `plugin.json` are regenerated (byte-equal to current in bundle mode).

## Command summary

| Command | Description |
|---------|-------------|
| `vd init` | Create `skills.toml` at the repo root |
| `vd add <source>/<path>` | Register an upstream skill in `skills.toml` |
| `vd list` | Print tracked skills as a table |
| `vd sync [skill...]` | Vendor tracked/pinned skills into `skills/`; runs `vd build` |
| `vd update [skill...]` | Bump tracked skills to upstream HEAD |
| `vd diff <skill>` | Show diff between upstream cache and local `skills/<name>/` |
| `vd doctor` | Report drift between `skills.lock` and the local `skills/` tree |
| `vd pin <skill> <sha>` | Lock a skill to a specific commit SHA |
| `vd detach <skill>` | Stop tracking a skill; leaves files on disk untouched |
| `vd remove <skill>` | Remove a skill from manifest, lock, and (by default) disk |
| `vd build [target...]` | Emit `marketplace.json`, `plugin.json`, and `.agents/` symlinks |
| `vd cache clean` | Delete the `.vd-cache/` download cache |

## Global flags

| Flag | Short | Description |
|------|-------|-------------|
| `--quiet` | `-q` | Suppress non-error output |
| `--verbose` | `-v` | Verbose output (reserved) |
| `--root` | | Override repo root path (takes precedence over `VD_ROOT`) |
| `--version` | | Print `vd <version>` |

Repo root resolution order: `--root` flag → `VD_ROOT` env var → walk up from CWD to the first `.git/`. Both `--root` and `VD_ROOT` are validated (must exist, must be a directory) and error out on invalid values rather than silently falling through.

## Documentation

- [Command reference](docs/commands.md) — flags, examples, exit codes per verb
- [Config schema](docs/config-schema.md) — full `skills.toml` field reference
- [FAQ](docs/faq.md) — naming, conflicts, dirty-refuse, and design decisions
- [Migration guide](docs/migration.md) — from manual copy-paste, git subtree, or submodules
- [Contributing](CONTRIBUTING.md) — dev setup, release flow, conventional commits
- [Changelog](CHANGELOG.md) — version history for the CLI
