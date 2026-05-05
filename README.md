# vanducng/skills

Duc's personal [Claude Code skills](https://code.claude.com/docs/en/skills) and the **`vd`** CLI for managing them.

![validate](https://github.com/vanducng/skills/actions/workflows/validate.yml/badge.svg)

## What's here

- **Skills** — packaged as the `vd` Claude Code plugin (`vd:research`, `vd:computer-clean`, …).
- **`vd` CLI** — a standalone Go binary for tracking, vendoring, and publishing Claude skills across repos.

## Install the skills (Claude Code plugin)

Inside Claude Code:

```
/plugin marketplace add vanducng/skills
/plugin install vd@vanducng-skills
```

Update later:

```
/plugin marketplace update vanducng-skills
/plugin install vd@vanducng-skills
```

Uninstall: `/plugin uninstall vd@vanducng-skills`.

## Install the `vd` CLI

Homebrew (recommended):

```sh
brew install vanducng/tap/vd
```

Or via curl (downloads the latest release for your platform):

```sh
curl -fsSL https://raw.githubusercontent.com/vanducng/skills/main/install.sh | sh
```

Quick start:

```sh
vd init && vd add browserbase/skills/browser --as browser && vd sync && vd build
```

Set `VD_ROOT` in your shell to use `vd` from any directory without `--root`. Full command reference: [`tools/vd/README.md`](tools/vd/README.md).

## Layout

```
.claude-plugin/   plugin manifest + marketplace registration
skills/           one directory per skill (each has SKILL.md)
tools/vd/         vd CLI source (Go module)
scripts/          install + new-skill helpers
```

## Contribute a skill

```bash
bash scripts/new-skill.sh my-new-skill
$EDITOR skills/my-new-skill/SKILL.md
bash scripts/validate.sh
git add skills/my-new-skill && git commit -m "feat: add my-new-skill" && git push
```

After pushing, users update via `/plugin marketplace update vanducng-skills`.

## License

[MIT](LICENSE)
