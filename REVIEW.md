# Review guide

Read `AGENTS.md` first. It holds the rules a change here is reviewed against: layout, commands, naming, portability, documentation sync and commits. This file says how a review is run and reported. It adds only the few rules that live in CI or in the release flow rather than in `AGENTS.md`.

## What you read

- Round 1: the whole change, `git diff $(git merge-base origin/main HEAD)..HEAD`, on the exact head sha, after CI has run on it.
- Round 2 on: only `git diff <last-reviewed-sha>..HEAD`. Do not re-read or re-post what you already reviewed.
- The pull request body, and the linked issue or plan, for what the change is meant to do.

## Two axes, two results

Report each axis on its own line; never blend them.

- **Spec:** the change does what its issue or plan asks, and nothing it does not ask. A skill that now triggers on requests it should leave to another skill, or stops triggering on its own, is a finding.
- **Standards:** the change follows `AGENTS.md` and the rules below.
- **Security** (a third axis, for a script that runs commands, reads credentials, serves on a port, or writes outside its own directory): input reaching a shell or a path, secrets printed or logged, a listener bound wider than it needs, and a check that fails open.

## Rules a reviewer checks that `AGENTS.md` does not state

- **Public repository.** No organisation, client, person, host or vault name, no personal absolute path, and no private URL, in the diff or the pull request body. Fixtures are synthetic.
- **Docs move with the change.** A skill's `SKILL.md`, references and the docs pages about it are updated in the same pull request, except the catalog page and the skill count (one docs pull request per wave, per `AGENTS.md`).
- **Versions.** A changed skill bumps its `metadata.version` (patch for a fix, minor for new behaviour). `CHANGELOG.md` and `version.txt` belong to the release flow: a pull request does not edit them.
- **Tests that fail first.** A behaviour change in a script ships with a test that failed before it, run in CI when the skill already has a test file there. A changed skill text that has `evals/` ships with the eval that shows the change; a skill without evals does not need new ones for a text fix.
- **Descriptions.** The `description` stays at or under 1024 characters and says when to use the skill and when not to.

## Each finding

- One tag: **Important** (blocks the merge), **Nit** or **Pre-existing** (both go on the follow-up list).
- `file:line` on the new side, what is wrong, and a one-line fix.
- Name the class of problem and list every instance in the change at once.

## Not a finding

- What CI already enforces: frontmatter and the 1024-character limit (`scripts/validate.sh`), slop words (`scripts/check-slop.sh`), catalog and release versions (`scripts/check-release-versions.sh`, `scripts/check-release-tag-collision.sh`), the docs contract (`scripts/check-docs-site.sh --check`) and the skill tests in `.github/workflows/validate.yml`.
- A preference with no rule behind it in `AGENTS.md` or this file.
- Code or text the change does not touch, unless the change makes it wrong (then Pre-existing or Important, with the reason).

## Verdict

One line per axis on the head sha: `spec: PASS|FAIL`, `standards: PASS|FAIL` (and `security: PASS|FAIL` when it applies), then the findings. PASS on every axis with no Important finding is a pass. One verdict per head; a push after a pass needs a new verdict on the new head.

## Replies

The author answers every thread with one outcome, `Fixed in <sha8>: <line>`, `Not applicable: <reason>`, `Intentional: <reason>` or `Deferred: <reason>, tracked in <item>`, and resolves it in the same round. After round 3 without a pass, stop and reconsider the approach before another push.
