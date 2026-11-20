# Fallbacks when agent-desktop is not available

Use these only when `agent-desktop` cannot be installed or refuses a target. They have no refs, no stale-target check and no delivery disposition, so every action is blind: screenshot before and after each one.

## macOS

| Need | Command | Notes |
|---|---|---|
| Screenshot, whole display | `screencapture -x -D 1 "$TMPDIR/s.png"` | `-x` no sound; `-D` is 1-based. Pixels are 2x points on Retina |
| Screenshot, one window | `screencapture -x -l <CGWindowID> "$TMPDIR/w.png"` | Includes a shadow margin: do not take click points from it |
| Click at a point | `cliclick c:<x>,<y>` | Global logical points, same as `--xy` |
| Double / right click | `cliclick dc:<x>,<y>` / `cliclick rc:<x>,<y>` | |
| Type text | `cliclick t:'hello'` | Typing goes to the focused app |
| Key chord | `osascript -e 'tell application "System Events" to keystroke "s" using command down'` | Needs Automation permission for System Events |
| Click a menu item | `osascript -e 'tell application "System Events" to click menu item "Save" of menu "File" of menu bar 1 of process "TextEdit"'` | Semantic, no coordinates |
| Read UI element tree | `osascript -e 'tell application "System Events" to get entire contents of window 1 of process "X"'` | Slow on big apps |

Install: `brew install cliclick`. Peekaboo (`brew install openclaw/tap/peekaboo`) is a heavier macOS-only alternative with annotated screenshots, menu bar and dialog commands, and an MCP server; reach for it when agent-desktop is blocked and AppleScript is too coarse.

## Ubuntu

| Need | X11 session | Wayland session (GNOME default) |
|---|---|---|
| Screenshot | `import -window root "$TMPDIR/s.png"` (ImageMagick) or `gnome-screenshot -f` | `gnome-screenshot -f` (portal consent may prompt on screen); `grim` on wlroots desktops only |
| Click | `xdotool mousemove <x> <y> click 1` | `ydotool mousemove --absolute -x <x> -y <y>; ydotool click 0xC0` (needs `ydotoold` and `/dev/uinput` access) |
| Type | `xdotool type --delay 20 'hello'` | `ydotool type 'hello'` |
| Key chord | `xdotool key ctrl+s` | `ydotool key 29:1 31:1 31:0 29:0` (raw keycodes) |
| Focus a window | `xdotool search --name 'Text Editor' windowactivate` | No portable way; Wayland forbids it |

Install: `sudo apt install xdotool imagemagick gnome-screenshot` (X11) or `sudo apt install ydotool` (Wayland). Run them inside the graphical session: over SSH export the variables `scripts/preflight.sh` prints first.

A Wayland pointer path is fragile by design. When pixel work matters, ask the user to log in to "Ubuntu on Xorg" from the login screen's gear menu.
