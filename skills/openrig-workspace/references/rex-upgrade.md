# Upgrade or restart a Rex server on a fleet host

Read this before upgrading or restarting the Rex server on a host that runs rigs, or when Rex sessions
are missing after one. Checked against Rex Mac preview.23, Linux server preview.11 and OpenRig 0.7.x.

## What survives

| Thing | Survives a Rex restart? |
| --- | --- |
| Programs running directly in a Rex pane (agents, dev servers, shells) | Never. Stopping the server ends every PTY. Rex has no live handoff. |
| Rex sessions, labels, IDs, windows, splits, floating panes | Yes, on Mac preview.23+ and Linux preview.11+. Each pane comes back as a fresh shell in its last directory. |
| Scrollback, last command | No with Rex's own restore. rexurrect restores both (below). |
| OpenRig seats | Yes, when their tmux server and the OpenRig daemon were not started from a Rex pane (see Linux). Seats run in tmux, not in Rex. |
| OpenRig views from `rig terminal open` in Rex | Come back as plain shells, detached from their seats. Run `rig terminal open <rig>` again. |

The first restart onto a version that saves sessions restores nothing, because the old server never
saved. Bridge that one with rexurrect.

The running server version is the `version:` line of `rex -S <host> server status`.
`rex -S <host> version` prints the local CLI version, not the remote one.

## Linux: processes started from a Rex pane die with its unit

A Rex server run as a systemd user unit owns the cgroup of everything started in its panes, and that
includes a tmux server that daemonized from one. `systemctl --user restart <rex unit>` kills them all.
Before restarting, check where the seats' tmux server and the daemon live:

```sh
sock=$(jq -r '.socketPath // empty' ~/.openrig/tmux-server.json)   # the seats' tmux server; empty means the default
cat /proc/$(tmux ${sock:+-S "$sock"} display -p '#{pid}')/cgroup   # must not name the Rex unit
cat /proc/$(pgrep -f 'openrig.*daemon' | head -1)/cgroup
```

If either names the Rex unit, `rig down <rig>` first and `rig up <rig> --existing` after, or start
the daemon and tmux from their own unit (`systemd-run --user --unit=<name> ...`). On macOS the app's
server does not take tmux down with it.

## Debian and Ubuntu: the distro's `rex` is a different tool

The distro package `rex` is a Perl deployment tool that owns `/usr/bin/rex`. An unattended upgrade or a software updater can install it over the Rex multiplexer even with an apt pin. Symptoms: `rex ls` prints "No Rexfile found", `rig terminal open --provider rex` says Rex is unavailable, and the running server's `/proc/<pid>/exe` ends in `(deleted)`. The server keeps running; the next restart or reboot would not bring it back.

Fix without touching the server: install the cached `.deb` that matches the running server (`dpkg -i /var/cache/apt/archives/rex_<server version>_amd64.deb`, versions from `rex server status`), then `apt-mark hold rex`. Upgrade later on purpose with the procedure below, which lifts the hold for the one install. A stray `Rexfile.lock` in a repo is the Perl tool's, safe to delete.

## Procedure

One host at a time. If you run inside a Rex pane (`TERM_PROGRAM=rex`; `REX_SERVER` names its
server), restarting that server ends your own session: do that host last and hand its restart to
the human, with the step 5 commands to run after.

1. Check the running and the available version, and the seats (`rig ps --nodes`).
   - Running: the `version:` line of `rex -S <host> server status`.
   - macOS: the app downloads a server update into
     `~/Library/Application Support/com.superlogical.rex/RexServer/Versions/<build>/` beside `Current/`
     (the running one) and switches on the next server restart. Read each with
     `"<dir>/Rex Server.app/Contents/MacOS/rex" version`.
   - Linux: `apt-cache policy rex` (Installed, Candidate from `pkgs.superlogical.com`), and
     `systemctl --user list-units | grep -i rex` for the unit.
2. Snapshot with rexurrect (below), always: it is cheap and covers scrollback.
3. On Linux, run the cgroup check above.
4. Upgrade. On macOS, restart the server from the app when it asks, which also applies the staged
   build. On Linux it needs the human's sudo:
   `sudo apt-mark unhold rex && sudo apt-get install --only-upgrade rex && sudo apt-mark hold rex`,
   then restart the server the way it was started (`systemctl --user restart <unit>`, or
   `rex server stop` then `rex server start`). `rex server stop` waits for the save to finish.
5. Check `rex -S <host> ls`, restore anything missing with rexurrect, then `rig ps --nodes` and
   `rig terminal open <rig>` for each rig you were watching.
6. Agents that ran directly in Rex panes need resuming: `pi -c`, `claude -c`, `codex resume --last`.

## rexurrect

<https://github.com/cemcatik/rexurrect> is a single binary for macOS and Linux that talks to Rex only
through the `rex` CLI and never starts a server. Install it with
`brew tap cemcatik/tap && brew install cemcatik/tap/rexurrect`, or the shell installer from its releases.
On Linux a `rexurrect-autosave` timer may already save every 15 minutes; its unit file names the
`REXURRECT_STATE_DIR` and `REX_SERVER` to use.

```sh
export REXURRECT_STATE_DIR=<dir>   # one dir per host keeps snapshots apart; mkdir -m 700 it first
export REX_SERVER=<host>           # a label from `rex hosts`; unset means the local server
rexurrect save                     # layout, cwd, last command, scrollback of every touched session
# upgrade and restart here
rexurrect restore --dry-run
rexurrect restore
```

- It skips sessions Rex already restored, because they keep their IDs, so it never duplicates.
- Its scrollback and typed commands apply only to sessions it creates. Start the server with
  `--restore=false` to have it rebuild everything. Rex's own saved sessions are kept for later.
- Commands are typed, never run, unless listed in `auto_resume` in its config. Pi has no built-in
  resume definition.
- Snapshots hold commands and scrollback, which can contain secrets. It keeps the state dir `0700`.
