---
name: verify
description: "Proves a change by running the same proof command on the parent commit and the head, each in a clean checkout, into an evidence manifest (fixed, regressed, same-pass, same-fail). Writes and ages verify-<app> skills: one app's boot, health and test commands. Use when asked to 'verify this change', 'prove the fix', 'run it before and after', 'QA this', 'does it actually work', 'make a verify skill for <app>', or 'is verify-<app> stale'. Not for reading the diff (vd:code-review)."
license: MIT
argument-hint: "[--base <ref>] [new <app> | stale <app>]"
metadata:
  author: vanducng
  version: "0.1.0"
---

# verify

The running half of the verdict: prove what the change does, before and after.

`S=<this skill's directory>/scripts`; `<base>` is the PR's base branch.

## Prove a change

1. **Pick the proof** from the record's proof contract:
   - a bug fix: the check that fails on the old code;
   - a feature: the flow on the real surface;
   - a refactor: the full test suite.
   Take the commands from the app's `verify-<app>` skill when there is one.
2. **Run both sides:** `bash "$S/both.sh" --base <base> --out <record>/proof/verify.json -- <command>`.
   - Each side runs in a clean temporary worktree, so include the install step (`-- sh -c 'npm ci && npm test'`).
   - A check the change adds is missing on the parent: pass `--from-head <test file>` to run it against the old code. A parent failing on a missing file proves nothing.
3. **Read the outcome** against the work type:

| Outcome | Bug fix | Feature | Refactor |
|---|---|---|---|
| `fixed` (parent fails, head passes) | proved | proved when the check is new | wrong: behavior changed |
| `same-pass` | not proved: the check does not catch the bug | fine for an old check; add the new one | proved |
| `regressed` or `same-fail` | blocks | blocks | blocks |

4. **UI:** a screenshot pair (parent, head), same viewport and data, saved beside the manifest.
5. **Attach:**
   - in a rig: `rig proof add --artifact-type qa` with `PASS` or `BLOCKING`, `--candidate-sha <head sha>`, and the outcome line as the money evidence;
   - outside a rig: the workbench record's `proof add`.
   Cite logs by their manifest sha256.
6. **Report:** outcome, both exit codes, the manifest path, what was not run.

## verify-<app> skills

- **New:** `node "$S/new-verify-app.cjs" <app> --repo <app repo> --out <skills dir>` reads the package.json scripts, Makefile targets and compose file into a command table, stamped `verified: <date> at <sha>`. Run each command once; fix any that fail before relying on it.
- **Upkeep:** `node "$S/stale.cjs" <skill dir> --repo <app repo> [--days 14]` exits 1 when the stamp is old or a listed command no longer exists. Report why; re-verify before refreshing the stamp.

## Rules

- **Evidence or nothing:** a claim without a manifest, log or screenshot is not a verdict.
- **Same command on both sides.**
- **Never fix the change.** A failure is a finding for the author.
