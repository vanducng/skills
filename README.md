# vanducng/skills

Duc's personal [Claude Code skills](https://code.claude.com/docs/en/skills), packaged as the **`vd`** plugin so skills appear in the catalog as `vd:<name>` and never collide with other plugins.

![validate](https://github.com/vanducng/skills/actions/workflows/validate.yml/badge.svg)

## Install (recommended — plugin marketplace)

Inside Claude Code:

```
/plugin marketplace add vanducng/skills
/plugin install vd@vanducng-skills
```

Skills become available as `vd:research`, `vd:computer-clean`, etc.

To update later:

```
/plugin marketplace update vanducng-skills
/plugin install vd@vanducng-skills   # re-installs current version
```

## Layout

```
.claude-plugin/
  marketplace.json    # registers plugin "vd"
  plugin.json         # plugin manifest (name: vd)
skills/
  research/SKILL.md         → vd:research
  computer-clean/SKILL.md   → vd:computer-clean
scripts/
  install.sh          # symlink fallback (dev/local edits — see below)
  uninstall.sh        # removes repo-owned symlinks
  new-skill.sh        # scaffold a new skill
  validate.sh         # frontmatter lint (CI)
.github/workflows/validate.yml
```

## Add a skill

```bash
cd ~/skills
bash scripts/new-skill.sh my-new-skill
$EDITOR skills/my-new-skill/SKILL.md   # fill description + body
bash scripts/validate.sh               # lint frontmatter
git add skills/my-new-skill && git commit -m "feat: add my-new-skill" && git push
```

After pushing, users update via `/plugin marketplace update vanducng-skills`.

## Symlink install (dev / local-edit fallback)

```bash
git clone https://github.com/vanducng/skills.git ~/skills
bash ~/skills/scripts/install.sh
```

This symlinks each `skills/<name>/` into `~/.claude/skills/<name>`. **Skills installed this way appear without the `vd:` prefix** (e.g. just `research`, not `vd:research`) — useful for fast iteration on a clone, but use the plugin path for the namespaced experience.

Conflict note: if you've installed via plugin AND symlink, you'll see duplicates. Pick one. Run `bash scripts/uninstall.sh` to drop the symlinks.

## Uninstall

Plugin install:

```
/plugin uninstall vd@vanducng-skills
```

Symlink install:

```bash
bash ~/skills/scripts/uninstall.sh
```

Removes only symlinks under `~/.claude/skills/` whose target resolves into this repo. Foreign files left untouched.

## Why per-skill symlinks (for the dev fallback)?

Top-level `~/.claude/skills/` symlinks have known bugs ([anthropics/claude-code#25367](https://github.com/anthropics/claude-code/issues/25367), [#14836](https://github.com/anthropics/claude-code/issues/14836)). Symlinking each skill folder individually works.

## License

[MIT](LICENSE)
