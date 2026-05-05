# Migration Guide

Recipes for adopting `vd` when you already manage upstream skills another way.

---

## From manual copy-paste

You have been copying skill directories from upstream repos by hand (no tooling).

### Step 1 — Initialize the manifest

```sh
cd ~/skills
vd init
```

This creates `skills.toml` seeded from the live `.claude-plugin/marketplace.json`.

### Step 2 — Register your existing hand-copied skills as detached

For each skill you copied manually, add a detached entry so `vd` knows about it without trying to sync it:

```sh
# Option A: edit skills.toml directly
# [skills.research]
#   mode = "detached"

# Option B: vd detach only works on already-tracked skills;
# for brand-new entries, add the block to skills.toml manually or use:
```

Or add them inline in `skills.toml`:

```toml
[skills.research]
  mode = "detached"

[skills.my-other-skill]
  mode = "detached"
```

Detached skills appear in `vd doctor` as `untracked (hand-authored or detached — OK)`.

### Step 3 — Register upstream sources for skills you want to keep in sync

For any skill where you do want to receive upstream updates:

```sh
vd add browserbase/skills/browser --as browser
```

`vd add` records the source and current SHA but does **not** overwrite the existing `skills/browser/` directory yet.

### Step 4 — Review the diff before syncing

```sh
vd diff browser      # compare upstream cache against your local copy
```

Decide whether to accept upstream changes (`vd sync browser`) or detach and keep your local version (`vd detach browser`).

### Step 5 — Sync and build

```sh
vd sync
# skills.lock is written, .claude-plugin/ is regenerated
```

---

## From git subtree

You used `git subtree add` to merge an upstream skill repo into your tree.

### Step 1 — Identify the subtree prefix

```sh
git log --all --oneline --grep="git-subtree-dir" | head -5
# Find commits like: "Add 'skills/browser/' from commit '...'"
```

The subtree prefix is the directory path (e.g. `skills/browser`).

### Step 2 — Back up any local changes

```sh
git diff HEAD skills/browser/   # review local patches
git stash                        # or commit them
```

### Step 3 — Remove the subtree tracking (optional)

Git subtrees do not store metadata in a config file — the only record is in commit messages. You can safely stop using `git subtree` commands without any cleanup step. The files remain.

### Step 4 — Register the skill with vd

```sh
vd init   # if skills.toml does not exist yet
vd add browserbase/skills/browser --as browser
```

At this point `skills.toml` has a `[skills.browser]` entry pointing at the upstream source, but `skills/browser/` still contains your subtree-managed files.

### Step 5 — Diff and decide

```sh
vd diff browser
```

- If upstream is ahead and you want the update: `vd sync browser`
- If you want to keep your local version: `vd detach browser`

### Step 6 — Commit

```sh
git add skills.toml skills.lock
git commit -m "chore: migrate browser skill from subtree to vd"
```

---

## From git submodule

You used `git submodule add` to link an upstream repo.

### Step 1 — Record the upstream URL and current SHA

```sh
cat .gitmodules
# [submodule "skills/browser"]
#   path = skills/browser
#   url = https://github.com/browserbase/skills

git submodule status
# abc1234f skills/browser (heads/main)
```

Note the URL and SHA — you will need them.

### Step 2 — Deinit and remove the submodule

```sh
git submodule deinit -f skills/browser
git rm -f skills/browser
rm -rf .git/modules/skills/browser
```

This removes the submodule link but leaves the working tree empty. You will repopulate it via `vd sync`.

### Step 3 — Commit the submodule removal

```sh
git add .gitmodules
git commit -m "chore: remove browser git submodule (migrating to vd)"
```

### Step 4 — Register with vd

```sh
vd init   # if skills.toml does not exist yet
vd add browserbase/skills/browser --as browser
vd sync browser
```

To pin to the exact SHA you were on before:

```sh
vd add browserbase/skills/browser --as browser --mode pinned
# vd add will record the current upstream HEAD SHA;
# if you need a specific old SHA, pin it afterward:
vd pin browser abc1234f
vd sync browser
```

### Step 5 — Verify

```sh
vd doctor
vd list
git diff .claude-plugin/   # expect empty diff in bundle mode
```

### Step 6 — Commit

```sh
git add skills.toml skills.lock skills/browser/
git commit -m "chore: migrate browser skill from submodule to vd"
```

---

## Converting a tracked skill to detached (keeping local edits)

You synced a skill, made local changes, and now want to keep them permanently without being refused on the next `vd sync`:

```sh
vd detach browser
# Output: detached browser (skills/browser/ unchanged)
```

After detaching:
- `skills/browser/` is untouched.
- The lock entry is removed.
- `vd sync` and `vd update` skip the skill.
- `vd doctor` reports it as `untracked`.

To re-attach later (accepting upstream changes):

```sh
vd add browserbase/skills/browser --as browser
vd sync browser --force   # --force because local tree differs from upstream
```
