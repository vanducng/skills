# vanducng/skills

Duc's personal [Claude Code skills](https://code.claude.com/docs/en/skills).

![validate](https://github.com/vanducng/skills/actions/workflows/validate.yml/badge.svg)

## Quick start

```bash
git clone https://github.com/vanducng/skills.git ~/skills
bash ~/skills/scripts/install.sh
# restart Claude Code, then:
/skills   # should list every skill in this repo
```

`install.sh` symlinks each `skills/<name>/` folder into `~/.claude/skills/<name>`. Edits in the repo are live in Claude Code on next session.

## Add a skill

```bash
cd ~/skills
bash scripts/new-skill.sh my-new-skill
$EDITOR skills/my-new-skill/SKILL.md   # fill description + body
bash scripts/validate.sh               # lint frontmatter
git add skills/my-new-skill && git commit -m "feat: add my-new-skill" && git push
```

The new skill is already symlinked (it lives inside the already-linked repo path under `~/skills/skills/`, but `install.sh` creates the per-skill symlink — re-run after adding).

```bash
bash scripts/install.sh   # idempotent, picks up the new skill
```

## Layout

```
skills/<name>/SKILL.md         # one folder per skill (kebab-case)
scripts/install.sh             # per-skill symlinks → ~/.claude/skills/
scripts/uninstall.sh           # removes only repo-owned symlinks
scripts/new-skill.sh           # scaffold new skill
scripts/validate.sh            # frontmatter lint (run by CI)
.claude-plugin/marketplace.json # /plugin marketplace add vanducng/skills
.github/workflows/validate.yml # CI
```

## Install via plugin marketplace (alternative)

Inside Claude Code:

```
/plugin marketplace add vanducng/skills
```

Currently a stub (`plugins: []`); the symlink path above is the supported install method.

## Uninstall

```bash
bash ~/skills/scripts/uninstall.sh
```

Removes only symlinks under `~/.claude/skills/` whose target resolves into this repo. Foreign files left untouched.

## Why per-skill symlinks?

Top-level `~/.claude/skills/` symlinks have known bugs ([anthropics/claude-code#25367](https://github.com/anthropics/claude-code/issues/25367), [#14836](https://github.com/anthropics/claude-code/issues/14836)). Symlinking each skill folder individually works.

## License

[MIT](LICENSE)
