# vanducng/skills

A daily-driver collection of [skills for agentic coding](https://code.claude.com/docs/en/skills) and the **`vd`** CLI for managing them.

![validate](https://github.com/vanducng/skills/actions/workflows/validate.yml/badge.svg)

## What's here

- **Skills** — packaged as the `vd` plugin for Claude Code (`vd:research`, `vd:computer-clean`, …).
- **`vd` CLI** — a standalone Go binary for tracking, vendoring, and publishing skills across repos.

## Install the skills (Claude Code plugin)

Inside Claude Code:

```
/plugin marketplace add vanducng/skills
/plugin install vd@vd-skills
```

Update later:

```
/plugin marketplace update vd-skills
/plugin install vd@vd-skills
```

Uninstall: `/plugin uninstall vd@vd-skills`.

## Install the `vd` CLI

The `vd` CLI lives in its own repo: [`vanducng/vd-cli`](https://github.com/vanducng/vd-cli).

Homebrew (recommended):

```sh
brew install vanducng/tap/vd
```

Or via `go install`:

```sh
go install github.com/vanducng/vd-cli/v2/cmd/vd@latest
```

Quick start:

```sh
vd init && vd add browserbase/skills/browser --as browser && vd sync && vd build
```

Set `VD_ROOT` in your shell to use `vd` from any directory without `--root`. Full command reference: [`vanducng/vd-cli` README](https://github.com/vanducng/vd-cli#readme).

## Layout

```
.claude-plugin/   plugin manifest + marketplace registration
skills/           one directory per skill (each has SKILL.md)
scripts/          dev helpers: new-skill, validate, dev-fallback symlinker
```

## Contribute a skill

```bash
bash scripts/new-skill.sh my-new-skill
$EDITOR skills/my-new-skill/SKILL.md
bash scripts/validate.sh
git add skills/my-new-skill && git commit -m "feat: add my-new-skill" && git push
```

After pushing, users update via `/plugin marketplace update vd-skills`.

## License

[MIT](LICENSE)
