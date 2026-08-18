---
title: "Getting Started"
---

Use the repo as either a published plugin catalog or a local skills workbench.

## Use A Published Skill

1. Install the catalog for your host from [Install](/install/).
2. Pick a canonical skill ID from [Skills](/skills/).
3. Invoke the skill in your agent UI.

Common entries:

| Goal | Skill |
| --- | --- |
| Align on what to build | `vd:interview` |
| Stress-test a plan or idea | `vd:interview --grill` |
| Scout a codebase | `vd:scout` |
| Debug a failure | `vd:debug` |
| Explore one-session approaches | `vd:brainstorm` |
| Chart a multi-session effort | `vd:wayfinder` |
| Plan a multi-step change | `vd:plan` |
| Execute a plan | `vd:cook` |
| Ship a branch | `vd:ship` |
| Update docs | `vd:docs` |

Source: `skills/<name>/SKILL.md` frontmatter.

## Edit A Skill

```sh
bash scripts/new-skill.sh my-skill
$EDITOR skills/my-skill/SKILL.md
bash scripts/validate.sh
```

:::note[Important]
Skill directory names are kebab-case and must match the `name` field in `SKILL.md`. The validator enforces this in `scripts/validate.sh`.
:::

## Sync Vendored Skills

`browser` and `browser-trace` are tracked from `browserbase/skills`, and `ego-browser` from `citrolabs/ego-lite`, in `skills.toml`. Use `vd` to inspect and update tracked sources:

```sh
vd list
vd sync
vd doctor
```

`vd doctor` reports tracked drift plus hand-authored or detached skills. In this repo, most `skills/*` directories are intentionally untracked local catalog entries.

## Release Changes

Use Conventional Commits. Release Please watches `main` and opens a release PR that keeps the skill-catalog version files aligned:

```text
version.txt
skills.toml
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
CHANGELOG.md
```

Source: `.github/workflows/release.yml`, `.release-please-config.json`, `scripts/check-release-versions.sh`.
