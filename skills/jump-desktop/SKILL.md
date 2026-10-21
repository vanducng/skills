---
name: jump-desktop
description: >
  Check and set up Jump Desktop remote access from the terminal on macOS and
  Linux hosts. Read a host's Jump Desktop Connect state (service, device id,
  real TCC grants, viewer Local Network grant, connection audit log), link a
  machine to an account with a Connect Code, and manage viewer connections as
  version-controlled .jump JSON files for RDP/VNC fallbacks. Use when the
  user mentions Jump Desktop, Jump Desktop Connect, JumpConnect, Fluid remote
  desktop, .jump or .jdz files, asks whether this machine is reachable
  remotely, why a remote connection failed (for example error 2.50), or wants
  to add a machine to Jump.
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
metadata:
  author: vanducng
  version: "1.0.0"
  bundle-id: com.p5sys.jump.connect
---

# Jump Desktop

Two apps, two roles:

| App | Role | Bundle id |
| --- | --- | --- |
| Jump Desktop Connect | host agent; a root service plus a per-user agent, links the machine to a Jump account (Fluid protocol, cloud relay, works from anywhere) | `com.p5sys.jump.connect`; Linux package `jump-connect` |
| Jump Desktop | viewer; connects to Connect hosts (listed automatically once signed in) and to plain RDP/VNC hosts | `com.p5sys.jump.mac.viewer` |

Connect runs on macOS, Windows, and Linux (deb/rpm `jump-connect`, 10.16+;
older support articles still say Linux is unsupported). Plain RDP/VNC `.jump`
entries are a fallback for when the cloud or the Connect service is down.

| | macOS | Linux |
| --- | --- | --- |
| binary | `/Applications/Jump Desktop Connect.app/Contents/MacOS/JumpConnect` | `/usr/libexec/jump/jumpconnect` |
| service | launchd `com.p5sys.jump.connect.service` | systemd `jump-connect.service`, user `jump-agent.service` |
| logs + `access.log` | `/Library/Logs/Jump Desktop/` | `/var/log/jump-connect/` |

Linux adds `--signin`, `--sessions`, `--disconnectsession <id>`,
`--disconnectuser <name>` (with `--json`; these need root).

## CLI

`scripts/jump-connect` wraps the `JumpConnect` binary (stripping its objc
noise) and the viewer's file handling. Run it from this skill directory, or
put it on `PATH`.

```bash
scripts/jump-connect status            # version, service/agent running, device id, TCC, last 5 access lines
scripts/jump-connect perms             # real TCC grants for the Connect service
scripts/jump-connect access 50         # connection audit log
scripts/jump-connect add-user <code>   # link this machine to an account (Connect Code, no GUI)
scripts/jump-connect sessions          # Linux: active sessions (sudo)
scripts/jump-connect list              # .jump entries in $JUMP_SERVERS_DIR
scripts/jump-connect open <name>       # launch one in Jump Desktop
scripts/jump-connect import            # save all entries into Jump Desktop's list
scripts/jump-connect bundle out.jdz    # just build the .jdz
```

`$JUMP_SERVERS_DIR` defaults to `$XDG_CONFIG_HOME/jump-desktop/servers`
(`~/.config/jump-desktop/servers`). Keep that directory in the user's dotfiles.

## Read state, do not guess it

- **Permissions:** `JumpConnect --dumpmacperm` reports the *calling terminal's*
  grants, so it says false from a shell even when the service is fully allowed.
  `perms` reads the system TCC DB instead. It needs Full Disk Access for the
  terminal; without it the command falls back to JumpConnect's own check, which
  is unreliable from a shell.
  Needed: `ScreenCapture`, `Accessibility`, `ListenEvent`, `RemoteDesktop`. A
  missing grant is fixed by the user in System Settings > Privacy & Security
  (`perms-ui` opens Jump's checker); never try to write TCC.db.
- **Account link:** `info` lists Connect-Code users only. An empty `users`
  array does not mean unlinked. Check `access` for `Type:Cloud` connections.
- **Audit log** (`/Library/Logs/Jump Desktop/access.log`, world-readable): each
  attempt logs request, established, `Authentication Succeeded|Failed` with
  `Type:Local` (macOS user + password) or `Type:Interactive` (someone at the
  host must click Allow). `Interactive ... Reason:Timedout` means nobody
  approved; for unattended use the viewer should log in with the macOS
  account. Report unknown emails or IPs to the user.
- **Viewer error 2.50 (0x32):** POSIX 50 `ENETDOWN` on the TCP connect. On
  macOS this is the viewer's **Local Network** privacy grant being denied: LAN
  addresses fail, mesh-VPN addresses (Tailscale `100.x`) still work. `status`
  prints `viewer LAN:`; the user fixes it in System Settings > Privacy &
  Security > Local Network
  (`open "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_LocalNetwork"`).
- **Logs:** service `/Library/Logs/Jump Desktop/Service_*.log`, agent
  `~/Library/Logs/Jump Desktop/Agent_*.log`, viewer (sandboxed)
  `~/Library/Containers/com.p5sys.jump.mac.viewer/Data/Library/Logs/Jump Desktop/Viewer_*.log`.
  `No route to host` for STUN/TURN over a `utun` interface means a full-tunnel
  VPN is eating WebRTC traffic.

## Set up a new machine

**Host with Connect (macOS, Windows, Linux):**

1. macOS: `brew install --cask jump-desktop-connect`. Linux: the `jump-connect`
   package from the Jump download page. Both auto-update.
2. Link it: the user creates a Connect Code in the Jump web dashboard, then
   `scripts/jump-connect add-user <code>`. Or sign in from the Connect app.
3. macOS: the user grants the four TCC permissions; confirm with `perms`.
4. Confirm with `status`, then a real connection from a viewer and the
   `access` log line.

**Fallback entries:** RDP to Linux (GNOME Remote Desktop: `grdctl status`,
`grdctl rdp enable`, `grdctl rdp set-credentials`) or VNC to macOS Screen
Sharing (port 5900). Use a LAN address for machines only reached at home and a
mesh-VPN name for a laptop that is reached from outside. Never store passwords
in the file.

## .jump files

One JSON object per connection. Minimal RDP entry:

```json
{
  "ConnectionTypeCode": 0,
  "DisplayName": "<host> (RDP)",
  "ProtocolTypeCode": 0,
  "TcpHostName": "<host>",
  "TcpPort": 3389,
  "TypeCode": 1,
  "UniqueId": "<uuidgen output>",
  "Username": ""
}
```

`ProtocolTypeCode`: 0 RDP, 1 VNC (Fluid is not a manual protocol; Fluid hosts
come from the account). Keep `UniqueId` stable across edits. Full key list:
`references/jump-file-format.md`.

- Opening a `.jump` file connects immediately and Jump **writes session state
  back into that file** (cert, timestamps); `open` therefore works on a temp
  copy so the version-controlled file stays clean.
- `import` opens a `.jdz`, which saves the entries into
  `~/Library/Containers/com.p5sys.jump.mac.viewer/Data/Documents/JumpDesktop/Viewer/Servers/`.
- Jump keeps usernames and passwords in the keychain and drops `Username` on
  import; the first connection prompts for both.

## Verify a viewer entry

After `open`, read the viewer log: `Connecting to: <host>:<port>` then
`Connected transport` proves reachability. RDP `Bad NTLM message signature` /
`credssp ... failed` right after means the host rejected empty or wrong
credentials, not a network problem.

## Boundaries

- Read-only by default. `add-user`, `raw --resetconfig`, `--removeconfig`,
  `--prepareclone`, `--uninstall` change or wipe the host: run only when asked.
- Never print or store passwords or Connect Codes in files or chat history
  beyond the single command that uses them.
- Uninstall needs admin: `sudo "/Applications/Jump Desktop Connect.app/Contents/MacOS/JumpConnect" --uninstall`.
