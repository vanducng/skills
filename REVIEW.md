# Review guide

Read `AGENTS.md` first. It holds the rules a change here is reviewed against: layout, commands, naming, portability, documentation sync and commits. This file says how a review is run and reported. It adds no rule of its own: a Standards finding cites `AGENTS.md`, a page under `docs/content/`, or a check.

## What you read

- Round 1: the whole change, `git diff $(git merge-base origin/main HEAD)..HEAD`, on the exact head sha, after CI has run on it.
- Round 2 on: only `git diff <last-reviewed-sha>..HEAD`. Do not re-read or re-post what you already reviewed.
- The pull request body, and the linked issue or plan, for what the change is meant to do.

## Two axes, two results

Report each axis on its own line; never blend them.

- **Spec:** the change does what its issue or plan asks, and nothing it does not ask.
- **Standards:** the change follows `AGENTS.md` and the rules below.
- **Security** (a third axis, for a script that runs commands, reads credentials, serves on a port, or writes outside its own directory): input reaching a shell or a path, secrets printed or logged, a listener bound wider than it needs, and a check that fails open.

## Where the Standards rules are written

- **Portability** (`AGENTS.md`, Coding Style): no personal absolute path, username or machine-only location; use repository-relative paths, `$HOME`, environment variables or hook-injected roots.
- **Documentation sync** (`AGENTS.md`, Documentation Sync): when a skill is added, removed, renamed or materially changed, its `SKILL.md`, references and the docs pages about it change in the same pull request. The exception is the catalog page and the skill count, which are updated in one docs pull request per wave.
- **Release versions** (`docs/content/development-guidelines.md`): the skill-catalog release versions are edited only in the Release Please pull request.
- **Validation and pull requests** (`AGENTS.md`, Testing Guidelines and Commit & Pull Request Guidelines): the commands it names are run, Conventional Commits with no AI tool named, and a pull request lists its validation commands and shows sample output or screenshots when it changes rendered assets, browser UI, diagrams or CLI output.

## Each finding

- One tag: **Important** (blocks the merge), **Nit** or **Pre-existing** (both go on the follow-up list).
- `file:line` on the new side, what is wrong, and a one-line fix.
- Name the class of problem and list every instance in the change at once.

## Not a finding

- What CI already enforces: frontmatter and the 1024-character limit (`scripts/validate.sh`), slop words (`scripts/check-slop.sh`), catalog and release versions (`scripts/check-release-versions.sh`, `scripts/check-release-tag-collision.sh`), the docs contract (`scripts/check-docs-site.sh --check`) and the skill tests in `.github/workflows/validate.yml`.
- A preference with no rule behind it in `AGENTS.md`, `docs/content/` or a check.
- Code or text the change does not touch, unless the change makes it wrong (then Pre-existing or Important, with the reason).

## Verdict

One line per axis on the head sha: `spec: PASS|FAIL`, `standards: PASS|FAIL` (and `security: PASS|FAIL` when it applies), then the findings. PASS on every axis with no Important finding is a pass. One verdict per head; a push after a pass needs a new verdict on the new head.

## Replies

The author answers every thread with one outcome, `Fixed in <sha8>: <line>`, `Not applicable: <reason>`, `Intentional: <reason>` or `Deferred: <reason>, tracked in <item>`, and resolves it in the same round. After round 3 without a pass, stop and reconsider the approach before another push.
