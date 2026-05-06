# FAQ

---

## Why is the CLI called `vd` when there's already a `vd` Claude plugin?

Both belong to the same user and repo — this is intentional duplication, not a conflict.

- **The Claude plugin** named `vd` is the skill bundle that users install via `/plugin install vd@vanducng-skills`. It lives in `.claude-plugin/` and appears in Claude Code as `vd:research`, `vd:plan`, etc.
- **The CLI binary** named `vd` is a Go program in `tools/vd/` that manages the skill repo (fetch, sync, build). It runs in your terminal.

The two artifacts share a name because they belong to the same ecosystem. The CLI *builds* the plugin. There is no runtime conflict: one is a PATH binary, the other is a Claude Code plugin identifier.

---

## Does `vd` conflict with `visidata` (which also uses `vd`)?

Possibly, if you have `visidata` installed. Both install a binary named `vd`.

Options:
- **Alias one of them:** add `alias vd-skills=/usr/local/bin/vd` or `alias vd-csv=~/.local/bin/vd` to your shell profile.
- **Use the full path:** call `./tools/vd/vd` from the repo root instead of relying on PATH resolution.
- **Rename the build output:** `make build BINARY=skill` produces a `skill` binary you can put on PATH under a different name.

The conflict is acknowledged and accepted. Most users of this repo do not use visidata interactively; those who do can alias safely.

---

## What does "refuse-on-dirty" mean and why does it exist?

When `vd sync` detects that a skill directory has been modified locally (filesystem tree hash differs from the hash recorded in `skills.lock` at last sync), it **refuses to overwrite** and prints:

```
REFUSED  browser — local edits detected
         run: vd detach browser  (keep edits) or use --force (overwrite)
```

This protects work. Without this guard, a `vd sync` or `vd update` would silently discard local patches you made to a vendored skill.

**Your options when refused:**

| Intent | Command |
|--------|---------|
| Keep your edits, stop syncing | `vd detach browser` then edit freely |
| Discard your edits, fetch upstream | `vd sync --force browser` |
| Inspect what changed | `vd diff browser` |

The refuse-on-dirty check only triggers when a `TreeHash` was recorded at last sync. Skills synced before `skills.lock` recorded tree hashes will fall through to a normal fetch.

---

## Why keep the CLI in the same repo as the skills it manages (monorepo)?

Single source of truth. Changes to the build tooling and to the skills they manage are atomic — one PR, one review, one tag. You never have "tool is at v1.2 but skills are at v0.9" drift.

The alternative (separate repo for the CLI) would mean:
- Cross-repo PRs for coordinated changes.
- Keeping two repos in sync when the schema evolves.
- Publishing the CLI separately before skills can use new features.

The CLI is scoped to `tools/vd/` with its own `go.mod`, path-filtered CI, and GoReleaser config — it behaves like a separate module without the overhead of a separate repo.

---

## Why not use `git subtree` or `git submodule`?

**Subtrees** merge upstream history into your repo. Pulling updates requires `git subtree pull`, which is non-obvious, and the commit history becomes noisy. Reverting a subtree update is painful.

**Submodules** require everyone cloning the repo to run `git submodule update --init`. They pin to a specific commit but the update workflow (`git submodule update --remote`) is error-prone and the `.gitmodules` file does not convey intent as clearly as `skills.toml`.

`vd` gives you:
- An explicit manifest (`skills.toml`) with human-readable intent.
- Atomic copy (not a git object — the skill content is just files in your tree).
- Dirty-check before overwriting.
- A `skills.lock` for reproducible installs.

The tradeoff: upstream Git history is not preserved in your repo. That is intentional — you vendor the *content*, not the history.

---

## What if two upstream sources have a skill with the same name?

`vd add` will detect the collision and error:

```
skill "browser" already tracked; use --as <alias> to register under a different name
```

Use `--as` to assign a local alias:

```sh
vd add browserbase/skills/browser --as bb-browser
vd add myorg/skills/browser --as my-browser
```

Both skills will coexist as `skills/bb-browser/` and `skills/my-browser/`.

---

## What takes priority: `[plugin.<name>]` overrides or SKILL.md frontmatter?

`[plugin.<name>]` overrides win. The full precedence chain (highest → lowest):

1. `[plugin.<name>]` in `skills.toml`
2. `SKILL.md` YAML frontmatter (`name`, `description`)
3. Lock-derived defaults (SHA short, mtime)
4. `[targets.claude.bundle]` defaults
5. Hard-coded fallbacks (`version = "0.0.0"`, `category = "utilities"`)

Use `[plugin.<name>]` when you want to override an upstream skill's description for your specific context without editing the vendored file (which would be detected as a local edit and block future syncs).

---

## Bundle mode vs per-skill mode — which should I use?

**Use bundle mode (the default).** Here is why:

| | Bundle mode | Per-skill mode |
|--|-------------|----------------|
| Plugin installs | One: `/plugin install vd@vanducng-skills` | One per skill (fragmented) |
| First-run byte-equality | Yes (seeded from live `marketplace.json`) | No — changes existing install paths |
| Namespace in Claude | `vd:<skill>` | `<skill>:<verb>` (no shared prefix) |
| Adding a new skill | Transparent — users get it on next update | Requires users to `/plugin install` the new entry |
| Risk on `main` | Low | High — breaks existing installs if switched |

Per-skill mode is useful for exploration (generate and inspect output in a throwaway branch) or for repos where each skill is truly a standalone product with its own versioning. It is not suitable as the default for a personal skill library.

---

## How does `.agents/` work?

`vd build` (via the `agents` emitter) creates a `.agents/skills/` directory at the repo root. Each entry is a relative symlink pointing at the corresponding `skills/<name>/` directory:

```
.agents/
  skills/
    browser       -> ../../skills/browser
    browser-trace -> ../../skills/browser-trace
    research      -> ../../skills/research
    ...
```

This directory matches Codex's repo-scoped skill discovery path. It mirrors `skills/` without duplicating files.

`.agents/` is gitignored by convention (the symlinks are regenerated by `vd build`). If you want to commit the symlinks, remove `.agents/` from `.gitignore`.

On Windows, `vd build` falls back from symlinks to directory copies (no symlink privilege required).

---

## Can I use `vd` for skills that I author locally (not from an upstream)?

Yes. Set `mode = "detached"` in `skills.toml`:

```toml
[skills.my-skill]
  mode = "detached"
```

Or use `vd detach my-skill` on an existing tracked skill. Detached skills appear in `vd list` and `vd doctor` (as `untracked` if not in the lock, or with status from the lock if they were synced before detaching), but `vd sync` and `vd update` always skip them.

You can also just create a `skills/<name>/` directory without any manifest entry — `vd doctor` will report it as `untracked (hand-authored or detached — OK)`.

---

## Why does `vd sync` run `vd build` automatically?

To keep `.claude-plugin/` always consistent with `skills/`. After syncing a new skill, users expect to be able to install it immediately via Claude Code. Requiring a separate `vd build` step would be easy to forget.

Use `vd sync --no-build` if you are syncing multiple times in a scripted workflow and want to build only once at the end.
