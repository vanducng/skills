# Fleet workspace sync

Use for the shared projects workspace across macOS laptops, macOS desktops, and Linux hosts. Read the workspace `AGENTS.md`, `fleet/machines.yaml`, and current `fleet/bin/workspace-sync` before taking action. Host names, SSH aliases, paths, job labels, and project ownership come from that workspace and the live host, never from this reference.

## "Sync fleet"

The operator's words "sync fleet" (or "fleet sync", "sync all hosts") authorize the default `fleet-sync` run: pulls, skill installs and capture copies on every host. They do not authorize committing, stashing, resetting or cleaning another host's dirty files, or touching rigs.

1. `fleet/bin/fleet-sync --check` from the workspace root. Read every `!` line. Then check the host identity: the block marked `(local)` must be the machine whose `hostname:` in `fleet/machines.yaml` matches `hostname -s`, and every other block must reach a different box (`ssh <alias> hostname -s`). If the tool labels the wrong machine local, two blocks describe the same box, or a registered host has no block of its own, the run is incomplete; trust none of its rows for the misidentified hosts.
2. `fleet/bin/fleet-sync`. It is idempotent, so run it even when nothing is behind: it also copies missing cited captures.
3. `fleet/bin/fleet-sync --check` again. A `!` that survives is a finding, not noise.
4. Report one row per host (repos behind and dirty, skills release, rigs running and needing attention), then each surviving `!` with its cause and the one command that fixes it. List dirty files by path and leave them; say whose they likely are.
5. A host the tool did not truly reach still gets synced, within the same authority: over its ssh alias, `git fetch` and `git pull --ff-only` in each working repo, then report its heads, behind counts and dirty paths. Never stash, reset or clean there. Report the tool defect separately and route its fix to the workspace's owner rig as a bugfix slice; do not patch fleet tooling from the operator session.

Known traps:

- `Cannot rebase onto multiple branches` on a pull: another pull ran at the same moment. Retry with `git fetch origin && git rebase --autostash origin/main`.
- An autostash that fails to apply leaves unmerged paths and keeps the stash. Copy each conflicted file aside (the workspace's gitignored scratch dir) before resolving, check every other stashed file made it into the working tree, then drop that stash by its hash. Never a bare `git stash pop`, never another stash.
- Records not committing on a host: read the workspace-sync log there. A secret-scanner hit blocks every record commit on that host until the allowlist or the record is fixed.
- A host behind on skills after a skills commit: hosts that install from releases get it only after the next release.
- Every host reporting the default machine as `(local)`, or `unknown host id '<openrig id>'` on a rig probe for the host you run from: the tool picked the local machine from a registry flag such as `access: local` instead of the hostname. The default machine was never reached. Apply step 5 to it.

## Start with the workspace's fleet command

If the workspace has `fleet/bin/fleet-sync`, run it before checking hosts by hand. `fleet-sync --check` reports every host's skills, dotfiles and projects checkouts, installed skills, scheduled sync results, Rex server and rigs, read-only. The default run also pulls, installs skills and copies cited captures, so it needs the same authority as running the sync jobs. `--list` names its modules; `--host` and `--only` narrow a run. Use the manual steps below for whatever it flags.

## Resolve hosts and authority

Build a row per registered host with its machine ID, access method, OS, physical workspace path, scheduler, latest workspace result, and ahead/behind counts. Report unreachable hosts as unverified. Resolve `$PROJECTS_ROOT` on each host, defaulting to its own `$HOME/projects`, then use `pwd -P` to detect an external volume. Do not expand the local user's home into remote commands.

The workspace syncs records through Git. Each host commits only records for projects pinned to it; discover that set with `fleet/bin/project-host --here`. Task directories, worktrees, caches, captures, and secrets do not move through record sync. Check the project's `host:` before creating work on a host. Sync does not grant permission to start a rig elsewhere or commit another host's records.

Investigations stay read-only. Running the sync script can stage, commit, rebase, autostash, and push; inspect it and confirm those effects are within the current authorization first. Editing this skill does not authorize running fleet sync. Do not invoke the whole repository sync wrapper merely to test one workspace.

## Check each host

Read current branch and dirty paths, then compare local, cached remote, and advertised remote heads:

```bash
cd "${PROJECTS_ROOT:-$HOME/projects}"
git status --short --branch
git rev-parse HEAD origin/main
GIT_TERMINAL_PROMPT=0 git ls-remote origin refs/heads/main
git rev-list --left-right --count HEAD...origin/main
```

The counts mean local-only / remote-only commits. They use the cached `origin/main`; if its hash differs from the advertised head, refresh with `git fetch origin` and recalculate before reporting divergence. Use the configured branch and remote when they differ from this example. A successful `ls-remote` proves remote access, not branch convergence or write permission.

Inspect the installed `git-sync-repos` wrapper, not just the workspace script. Read both `$HOME/.local/log/git-sync-repos.log` and `$HOME/.local/log/workspace-sync.log`, if present, and compare their timestamps with the fix and the host's current time. Check `$HOME/.local/state/workspace-sync.paused`, if supported. Old successes and old failures do not verify a new fix.

| Host OS | Scheduler evidence |
|---|---|
| macOS | Discover the launch agent label and plist from the installed setup. Inspect `launchctl print "gui/$(id -u)/<label>"`, its arguments, latest run, and logs. |
| Linux | Discover the installed user units. Inspect `systemctl --user list-timers --all`, the matching service, and `journalctl --user -u <service>`. |

The wrapper can exit zero while a child workspace sync fails. Require a fresh result from the workspace itself. If records were skipped because a secret scanner was unavailable or failed, an `ok: current` line proves only Git convergence; it does not prove dirty records were committed.

## Git credentials

Inspect helper ordering and source files without printing credentials:

```bash
git config --show-origin --show-scope --get-regexp '^credential.*helper$'
gh auth status
env -u GH_TOKEN -u GITHUB_TOKEN GIT_TERMINAL_PROMPT=0 git ls-remote origin HEAD
```

Use the `gh` checks for GitHub HTTPS remotes. SSH remotes need SSH authentication checks instead. Unsetting token variables distinguishes the persisted login used by unattended jobs from a working token in the interactive terminal. If write access needs verification, use `git push --dry-run origin HEAD:main`; a dry run does not prove an actual push will pass every server rule.

A helper that invokes a missing Python module can emit errors even when another helper authenticates successfully. If GitHub CLI already works, retain its host-specific helper and remove only the confirmed stale entry from the file that defines it. For example, after backing up that file, an obsolete global helper can be removed by exact value:

```bash
git config --global --fixed-value --unset-all credential.helper '<obsolete-helper>'
```

Do not clear all helpers, overwrite other host/account configuration, install an unrelated Python package, rotate a credential, or print the output of `git credential fill`. If no working helper exists, establish the intended account before changing its configuration. Rerun the original remote operation without shell tokens and check stderr as well as its exit code.

## macOS background disk access

`Operation not permitted` while launchd opens a script under an external volume can be a macOS privacy denial. An SSH shell reading that script does not prove `/bin/bash` in launchd can read it. Correlate the scheduler error with TCC logs for the responsible executable and volume service before assigning the cause.

When checking a reported fix before the next scheduled run, use a temporary launchd job with the same interpreter and launch context to run `/bin/bash -n` against the workspace script. This checks access and syntax without executing sync. Use a unique job label, write output outside the protected volume, inspect the result, and remove the probe job and files. A passing probe verifies that boundary only; require a subsequent real workspace result before declaring sync healthy.

If access remains denied, report the exact responsible executable and protected path. The operator must grant the relevant Files and Folders or Full Disk Access permission in System Settings. Do not edit the TCC database, disable platform protections, or move the workspace to evade the denial. Test again after the change; restarting a scheduler alone does not grant disk access.

## Divergence and completion

Ahead and behind at once means the branches diverged. Credentials or disk access may be fixed while divergence remains. Do not hand-merge, reset, force-push, or discard dirty records as a health check. Report the commits and affected record owners. When authorized to run the existing workspace sync, let its configured reconciliation path run once, inspect any failure, and stop repeated retries on the same conflict. Preserve WIP and any autostash; recovery must not drop it after a failed apply.

Before reporting success, collect a fresh workspace result on each host, compare its local head with the live remote, and inspect remaining dirty records. State separately whether credentials work, the background runner can access the workspace, history converged, and owned records were committed. Include unresolved permission, scanner, ownership, or conflict blockers. Never report fleet health from one host's result.
