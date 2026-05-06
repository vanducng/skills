# vd — Command Reference

One section per verb. All commands accept the global flags `--quiet` / `-q`, `--verbose` / `-v`, `--root <path>`, and `--version`.

**Repo root resolution.** Order: `--root` flag → `VD_ROOT` env var → walk up from CWD to the first `.git/`. Set `VD_ROOT` in your shell to pin a default repo when invoking `vd` from arbitrary directories. Both `--root` and `VD_ROOT` are validated (must exist, must be a directory).

**Upstream version check.** Each command runs a background lookup against the GitHub releases API, cached for 24 hours under `$XDG_CACHE_HOME/vd/version-check.json` (or `~/.cache/vd/version-check.json`). When a newer release exists, vd prints a single line to stderr: `vd 1.0.0 (latest: 1.1.0). Upgrade: brew upgrade vd`. The check is best-effort and silent on any failure. Disable globally with `VD_NO_UPDATE_CHECK=1`, suppress per-call with `--quiet`. Auto-disabled when `CI` is set, when the binary is a `dev` build, and when stderr is not a terminal.

---

## vd init

Create `skills.toml` at the repo root. Walks up from CWD to find `.git/`, or use `--root`.

On first run it reads `.claude-plugin/marketplace.json` (if present) and seeds the `[targets.claude.bundle]` defaults so `vd build` immediately produces byte-equal output.

**Signature:**
```
vd init [--force] [--root <path>]
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--force` | Overwrite an existing `skills.toml`. |
| `--root <path>` | Use this directory as the repo root instead of walking up. |

**Examples:**
```sh
vd init                      # create skills.toml at repo root
vd init --force              # regenerate from defaults (overwrites edits)
vd init --root /tmp/myrepo   # target a specific repo
```

**Side effects:** writes `skills.toml`. Does not touch `skills.lock` or any skill directories.

**Exit codes:** `0` success, `1` file already exists without `--force`, `1` no `.git/` found.

---

## vd add

Register an upstream skill in `skills.toml`. Fetches the upstream catalog to validate the path and record the current HEAD SHA. Does **not** copy files locally — use `vd sync` for that.

If the source name (`owner` in `owner/repo/path`) is not declared in `[sources]`, it is auto-registered as a GitHub HTTPS source.

**Signature:**
```
vd add <source>/<path> [--as <name>] [--mode tracked|pinned] [--ref <ref>] [--refresh]
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--as <name>` | Override the skill name in `skills.toml` (local directory name). Required when two sources share a skill name. |
| `--mode` | `tracked` (default) or `pinned`. Pinned locks to the resolved SHA immediately. |
| `--ref <ref>` | Override the branch/tag/SHA for this fetch (overrides `[sources.*].ref`). |
| `--refresh` | Bypass the cache TTL and re-fetch from upstream. |

**Examples:**
```sh
vd add browserbase/skills/browser
vd add browserbase/skills/browser --as bb-browser   # avoid name collision
vd add browserbase/skills/browser --mode pinned      # pin to current HEAD
vd add browserbase/skills/browser --ref v1.2.0       # fetch specific tag
```

**Side effects:** mutates `skills.toml` (adds `[sources.*]` if needed and `[skills.*]`). Updates the local git cache under `.vd-cache/`. Does not touch `skills.lock` or `skills/`.

**Idempotent:** re-running with the same source/path/mode is a no-op.

**Exit codes:** `0` success, `1` path not found in upstream catalog (lists available paths), `1` git not in PATH.

---

## vd list

Print tracked skills from `skills.toml` as a formatted table.

**Signature:**
```
vd list
```

**Output columns:**

| Column | Description |
|--------|-------------|
| `NAME` | Local skill name (directory under `skills/`). |
| `SOURCE` | Source key from `[sources.*]`. |
| `MODE` | `tracked`, `pinned`, or `detached`. |
| `SHA` | First 8 chars of the commit SHA from `skills.lock`. `-` if not yet synced. |
| `DRIFT` | Reserved; always `-` in the current release. |

**Examples:**
```sh
vd list
# NAME           SOURCE       MODE     SHA       DRIFT
# browser        browserbase  tracked  2a3bbb3b  -
# browser-trace  browserbase  tracked  2a3bbb3b  -
```

Prints `no skills tracked` and exits `0` on an empty manifest.

**Exit codes:** `0` always (informational command).

---

## vd sync

Fetch upstream content for all tracked and pinned skills (or a named subset) and copy them atomically into `skills/<name>/`. Updates `skills.lock`. Runs `vd build` automatically afterward unless `--no-build` is passed.

Skills with local modifications **refuse to sync** by default (see "refuse-on-dirty" in [FAQ](faq.md)). Detached skills are always skipped.

**Signature:**
```
vd sync [skill...] [--force] [--no-build]
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--force` | Overwrite skills that have local modifications without refusing. |
| `--no-build` | Skip the automatic `vd build` after a successful sync. |

**Examples:**
```sh
vd sync                        # sync all tracked/pinned skills
vd sync browser                # sync only the "browser" skill
vd sync browser browser-trace  # sync two skills
vd sync --force                # overwrite even locally modified skills
vd sync --no-build             # sync without regenerating plugin files
```

**Side effects:** writes or updates `skills/<name>/` directories atomically (stage → rename), updates `skills.lock`, and runs `vd build` (unless `--no-build`).

**Exit codes:** `0` success, `1` any skill refused (dirty) without `--force`, `1` fetch error.

---

## vd update

Re-fetch upstream HEAD for all `tracked` skills (or a named subset) and update `skills.lock`. Pinned and detached skills are skipped.

Internally calls the same sync logic as `vd sync` but filters to mode=tracked only.

**Signature:**
```
vd update [skill...] [--force]
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--force` | Overwrite skills that have local modifications without refusing. |

**Examples:**
```sh
vd update                 # bump all tracked skills to upstream HEAD
vd update browser         # bump only "browser"
```

**Side effects:** same as `vd sync` but restricted to tracked skills.

**Exit codes:** same as `vd sync`.

---

## vd diff

Show a diff between the cached upstream copy of a skill and the local `skills/<name>/` directory. Shells out to `git diff --no-index --color`.

**Signature:**
```
vd diff <skill>
```

**Examples:**
```sh
vd diff browser           # compare cache vs skills/browser/
```

**Exit codes:** `0` identical, `1` differences found (mirrors `git diff` semantics), `>1` error (git not found, cache missing, skill not in lock).

---

## vd doctor

Report drift between `skills.lock` entries and the current state of `skills/` on disk. Informational only — always exits `0`.

Reports three status values:

| Status | Meaning |
|--------|---------|
| `none` | Lock SHA matches filesystem tree hash. Clean. |
| `modified` | Filesystem tree hash differs from lock. Local edits present. |
| `missing` | Skill is in the lock but the `skills/<name>/` directory does not exist. |
| `untracked` | Directory exists in `skills/` but has no lock entry (hand-authored or detached). |

**Signature:**
```
vd doctor
```

**Examples:**
```sh
vd doctor
# SKILL           STATUS     DETAIL
# -----           ------     ------
# browser         none
# research        untracked  (hand-authored or detached — OK)
```

**Exit codes:** `0` always.

---

## vd pin

Lock a skill to a specific upstream commit SHA. Sets `mode = "pinned"` and records the SHA in `skills.toml`. Does **not** trigger a sync — run `vd sync` to apply.

**Signature:**
```
vd pin <skill> <sha>
```

The SHA must be at least 7 hex characters (short or full SHA both accepted).

**Examples:**
```sh
vd pin browser abc1234f
vd pin browser abc1234f0000000000000000000000000000000000   # full SHA OK
```

**Side effects:** mutates `skills.toml` (`mode = "pinned"`, `pin = "<sha>"`).

**Exit codes:** `0` success, `1` skill not in manifest, `1` invalid SHA format.

---

## vd detach

Stop tracking a skill from its upstream source. Sets `mode = "detached"`, clears `source`/`path`/`pin`, and removes the entry from `skills.lock`. The `skills/<name>/` directory is **left untouched** on disk.

After detaching, `vd sync` and `vd update` skip the skill entirely. You can edit the directory freely.

**Signature:**
```
vd detach <skill>
```

**Examples:**
```sh
vd detach browser         # keep files, stop syncing
```

**Side effects:** mutates `skills.toml` and `skills.lock`. Does not touch the filesystem skill directory.

**Exit codes:** `0` success (including already-detached no-op), `1` skill not in manifest.

---

## vd remove

Remove a skill from `skills.toml`, `skills.lock`, and (by default) from `skills/<name>/` on disk.

Without `--force`, refuses to delete the directory if it has local modifications (filesystem hash differs from lock). Use `vd detach` first if you want to keep the edits.

**Signature:**
```
vd remove <skill> [--keep-files] [--force]
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--keep-files` | Remove from manifest and lock but leave `skills/<name>/` on disk. |
| `--force` | Delete even if local modifications are detected. |

**Examples:**
```sh
vd remove browser                  # remove from manifest + disk
vd remove browser --keep-files     # untrack but keep the directory
vd remove browser --force          # delete even with local edits
```

**Side effects:** mutates `skills.toml` and `skills.lock`; may delete `skills/<name>/`.

**Exit codes:** `0` success, `1` skill not in manifest, `1` local modifications detected without `--force`.

---

## vd build

Emit plugin files for all configured targets. Reads `skills.toml` and `skills.lock`.

**Targets:**
- `claude` — writes `.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json`.
- `agents` — writes `.agents/skills/<name>` symlinks pointing at `skills/<name>/`.

With no arguments, both targets are built. Pass target names to build only those.

**Signature:**
```
vd build [target...]
```

**Examples:**
```sh
vd build                  # build all targets (claude + agents)
vd build claude           # regenerate marketplace.json and plugin.json only
vd build agents           # regenerate .agents/skills/ symlinks only
```

**Side effects:** writes `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json`, and `.agents/skills/<name>` symlinks. In bundle mode, output is byte-equal to the live files when manifest is seeded correctly.

**Exit codes:** `0` success, `1` unknown target name, `1` `skills.toml` not found.

---

## vd install

Install local skills into an agent environment. With no agent argument, `vd install` opens a terminal picker with these choices:

1. Codex user skills — symlink to `$HOME/.agents/skills` (default recommendation)
2. Codex repo skills — symlink to `.agents/skills`
3. Codex snapshot copy — copy to `$HOME/.agents/skills`
4. Claude Code plugin — marketplace/plugin install

Passing the agent is recommended for scripts.

**Agents:**
- `codex` — installs local `skills/<name>/` directories into Codex discovery paths. Default scope is user, which writes symlinks to `$HOME/.agents/skills`. Use `--scope repo` to write `.agents/skills/<name>` in the current repo.
- `claude` — runs `vd build claude`, registers this repo as a Claude Code marketplace, and installs the configured plugin bundle.

**Signature:**
```
vd install [agent] [skill...]
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--scope` | `codex`: `user` or `repo`; `claude`: `user`, `project`, or `local`. |
| `--dest` | Override Codex destination directory. |
| `--copy` | Copy Codex skills instead of symlinking. |
| `--force` | Replace existing Codex destination entries. |
| `--dry-run` | Print planned actions without changing files. |

**Examples:**
```sh
vd install codex                         # symlink all skills into $HOME/.agents/skills
vd install codex research plan           # install selected skills only
vd install codex --scope repo            # symlink all skills into .agents/skills
vd install codex --copy --force          # replace existing installs with copies
vd install                               # open the install target picker
vd install claude                        # install configured Claude Code plugin bundle
vd install claude --dry-run              # print Claude plugin commands
```

**Side effects:** `codex` writes symlinks or copies under the destination skill directory. `claude` may mutate Claude Code marketplace and plugin installation state.

**Exit codes:** `0` success, `1` invalid agent/scope, missing skill, existing destination without `--force`, or external Claude command failure.

---

## vd cache clean

Delete the `.vd-cache/` directory at the repo root. The cache stores sparse-cloned upstream repos and is repopulated on the next `vd add` or `vd sync`.

**Signature:**
```
vd cache clean
```

**Examples:**
```sh
vd cache clean            # remove .vd-cache/
```

**Side effects:** removes `.vd-cache/` entirely. Safe to run at any time; no manifest or skill data is touched.

**Exit codes:** `0` always (no-op if cache is already empty).
