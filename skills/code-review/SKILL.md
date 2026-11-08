---
name: code-review
description: "Gives the non-author verdict on a diff, one result per axis: Spec (does it do what the slice SPEC asks), Standards (does it follow the repo's REVIEW.md and AGENTS.md), and Security when the change is Deep. Writes a verdict file bound to the exact diff (patch-id plus digest), with tagged finding ids. A verdict, not a bug hunt: it never fixes and never delegates. Use when asked to 'review this PR', 'review the diff', 'code review', 'give the verdict', 're-review after the fix', or '--refactor'."
license: MIT
argument-hint: "[--base <ref>] [--post] [--refactor]"
metadata:
  author: vanducng
  version: "2.0.0"
---

# code-review

You judge someone else's diff. You never fix it and never delegate: do not invoke `code-review` again, spawn agents, or call another model's CLI.

`V=<this skill's directory>/scripts/verdict.cjs`; `<base>` is the PR's base.

## Steps

1. **Tier:** `node "$V" tier --base <base>` prints the tier and the axes it needs.
2. **Round:** `node "$V" round <record>/proof --seat <seat>` (your verdicts count; another seat's do not) exits 3 past round 3: stop and hand the approach to the lead. From round 2, read only `git diff <previous verdict head>..HEAD` and the open findings; repeat nothing.
3. **Read:**
   - for Spec: the slice `SPEC.md` (intent, mini-requirements, proof contract). No SPEC (a plain PR or commit): write `--spec inconclusive` and judge Standards;
   - for Standards: `REVIEW.md`, then `AGENTS.md`, else `references/checklist.md`;
   - whole files, not hunks.
4. **Judge each axis alone:** `pass`, `fail` or `inconclusive`, which blocks.
   - Spec fails on an unmet mini-requirement or contract item.
   - Standards fails on a broken written rule; quote the rule.
   - Security (Deep) covers injection, secrets, auth scope and migrations.
5. **Findings:** ids `F1`, `F2`, each with an axis, a tag (`Important` blocks, `Nit`, `Pre-existing`) and a status (`open`, `fixed`, `declined`).
   - Flag the class of bug, so every instance gets fixed.
   - A deliberate product choice is a question, not a finding.
6. **Write:** `node "$V" write --base <base> --out <file> --spec R --standards R [--security R] --finding "F1|spec|Important|open|<one line>" --seat <seat> --family <model family> --round N`. It binds the file to the diff and refuses a blended or impossible verdict.
7. **Attach:**
   - in a rig: `rig proof add --artifact-type rev1-r<N>` with the printed `verdict`;
   - outside one: the workbench record's `proof add`.
   Then run `fleet verdict-check <record> --base <base>` if `fleet` is on PATH, else `node "$V" check <file> --base <base>`.
8. **Report:** axis results, findings by id, the file path.

## Tiers

| Tier | When | Adds |
|---|---|---|
| Quick | docs only, or under 50 lines with no risky path | diff and touched files |
| Standard | anything else | lenses by path (schema, API, UI) |
| Deep | auth, secrets, migrations, CI, money, infra | `security` axis; run the failing case for each finding |

## Other modes

- `--refactor`: does it fit the codebase? Local only: `references/refactor.md`.
- `--post`: also post on the PR: `references/pr-comments.md`.
- Real data or downstream readers: `references/live-verification.md`.
- Breakage outside the diff: `references/blast-radius.md`.
