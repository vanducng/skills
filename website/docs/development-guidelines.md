---
title: "Development Guidelines"
---

## Skill Layout

Every skill lives in `skills/<name>/` and must include `SKILL.md`.

```text
skills/
  my-skill/
    SKILL.md
    scripts/
    references/
    assets/
```

Keep skill names kebab-case and match the `name` field in frontmatter to the directory name. `scripts/validate.sh` enforces this.

## Writing Skills

- Keep `SKILL.md` focused on trigger conditions and workflow.
- Put long reference material under `references/`.
- Put deterministic helpers under `scripts/`.
- Put templates, images, and copied output assets under `assets/`.
- Use canonical IDs like `vd:cook`, `vd:docs`, or `vd:zensical` when referring to skills in docs.

Source: `skills/skill-management/SKILL.md`, `scripts/validate.sh`.

## Local Commands

```sh
bash scripts/new-skill.sh my-new-skill
bash scripts/validate.sh
bash scripts/check-release-versions.sh
vd list
vd doctor
zensical build --clean --strict
```

## Release Hygiene

Use Conventional Commits. Focus scopes on the changed component:

```text
feat(zensical): add docs-site skill
fix(skill-management): update vd-cli module path
docs: publish zensical site
```

Do not manually edit skill-catalog release versions unless you are working in the Release Please PR. The release workflow owns those version bumps.

## Documentation Rules

Canonical shared docs live in `README.md` and `docs/`. Project journals and one-off reports should stay out of `docs/` so the published site remains durable.

Public docs should cite the files they describe. If a claim cannot be traced to source, either remove the claim or add the missing source.
