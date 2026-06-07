#!/usr/bin/env bash
# install-hooks.sh — register (or remove) pursue's Codex hooks in
# ~/.codex/config.toml. Sub-verb for `vd:pursue install-hooks` (#61).
#
# Strategy: NO TOML rewrite (no tomlkit/tomli_w in the venv, and the config is
# commonly a hand-maintained dotfiles symlink). We append a MARKER-wrapped block
# of `[[hooks.PostToolUse]]` / `[[hooks.SessionStart]]` array-of-tables to the
# end of the file — TOML-valid, idempotent (keyed on the marker), and cleanly
# removable. A backup + tomllib re-parse guards every write.
#
# Usage:
#   install-hooks.sh                 detect + print the block to add (NO write)
#   install-hooks.sh --apply         write the block if missing (idempotent)
#   install-hooks.sh --uninstall     remove the managed block
#   install-hooks.sh --config <path> target a non-default config
#
# Exit: 0 ok/idempotent · 2 bad-args/usage · 3 missing→needs --apply / conflict · 4 write/parse failure
set -uo pipefail

CONFIG="${HOME}/.codex/config.toml"
MODE="detect"
while [ $# -gt 0 ]; do
  case "$1" in
    --apply)     MODE="apply"; shift ;;
    --uninstall) MODE="uninstall"; shift ;;
    --config)    CONFIG="${2:?--config needs a path}"; shift 2 ;;
    -h|--help)   grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "install-hooks.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done

PYBIN="${HOME}/.claude/skills/.venv/bin/python3"; [ -x "$PYBIN" ] || PYBIN="$(command -v python3)"

# Resolve a symlinked config to its real target so writes land where the user
# (and their dotfiles repo) actually keep it.
REAL="$CONFIG"
if [ -L "$CONFIG" ]; then REAL="$(cd "$(dirname "$CONFIG")" && cd "$(dirname "$(readlink "$CONFIG")")" 2>/dev/null && pwd)/$(basename "$(readlink "$CONFIG")")"; fi

MODE="$MODE" CONFIG="$CONFIG" REAL="$REAL" "$PYBIN" - <<'PY'
import os, sys, time, tomllib

mode   = os.environ["MODE"]
cfg    = os.environ["CONFIG"]
real   = os.environ["REAL"]

START = "# >>> vd:pursue managed hooks >>>"
END   = "# <<< vd:pursue managed hooks <<<"
CMD_MON = "bash ~/.agents/skills/pursue/scripts/codex-monitor-hook.sh"
CMD_CLN = "bash ~/.agents/skills/pursue/scripts/codex-hook-cleanup.sh"

BLOCK = f"""{START}
[[hooks.PostToolUse]]
matcher = ".*"

[[hooks.PostToolUse.hooks]]
type = "command"
command = "{CMD_MON}"

[[hooks.SessionStart]]
matcher = ".*"

[[hooks.SessionStart.hooks]]
type = "command"
command = "{CMD_CLN}"
{END}
"""

def warn_symlink():
    if os.path.realpath(cfg) != os.path.abspath(cfg):
        print(f"⚠  {cfg} is a symlink → {os.path.realpath(cfg)}")
        print("   Editing it modifies that (likely dotfiles) file — commit it there if version-controlled.")

text = ""
if os.path.exists(real):
    text = open(real, encoding="utf-8").read()
present = (START in text) or (CMD_MON in text and CMD_CLN in text)

if mode == "detect":
    if present:
        print(f"✓ pursue Codex hooks already registered in {cfg}")
        sys.exit(0)
    print(f"✗ pursue Codex hooks NOT registered in {cfg}")
    warn_symlink()
    print("\nAdd this block (or re-run `vd:pursue install-hooks --apply`):\n")
    print(BLOCK)
    sys.exit(3)

if mode == "apply":
    if present:
        print(f"✓ already registered (idempotent no-op): {cfg}")
        sys.exit(0)
    if not os.path.exists(real):
        print(f"✗ config not found: {real} — create ~/.codex/config.toml first", file=sys.stderr)
        sys.exit(4)
    warn_symlink()
    bak = f"{real}.bak-{int(time.time())}"
    open(bak, "w", encoding="utf-8").write(text)
    new = text + ("" if text.endswith("\n") else "\n") + "\n" + BLOCK
    open(real, "w", encoding="utf-8").write(new)
    try:
        tomllib.load(open(real, "rb"))
    except Exception as e:
        open(real, "w", encoding="utf-8").write(text)  # restore
        print(f"✗ write produced invalid TOML ({e}); restored original. Backup: {bak}", file=sys.stderr)
        sys.exit(4)
    print(f"✓ appended pursue hooks to {real} (backup: {bak})")
    print("  Restart your Codex session so the hooks load. Codex will prompt to trust the new hook commands on first run.")
    sys.exit(0)

if mode == "uninstall":
    if START in text and END in text:
        bak = f"{real}.bak-{int(time.time())}"
        open(bak, "w", encoding="utf-8").write(text)
        i, j = text.index(START), text.index(END) + len(END)
        new = text[:i] + text[j:]
        # tidy stray blank lines around the removed block
        new = new.replace("\n\n\n", "\n\n")
        open(real, "w", encoding="utf-8").write(new)
        try:
            tomllib.load(open(real, "rb"))
        except Exception as e:
            open(real, "w", encoding="utf-8").write(text)
            print(f"✗ removal produced invalid TOML ({e}); restored. Backup: {bak}", file=sys.stderr)
            sys.exit(4)
        print(f"✓ removed pursue managed hooks from {real} (backup: {bak})")
        sys.exit(0)
    if CMD_MON in text or CMD_CLN in text:
        print(f"✗ pursue hooks present but NOT marker-wrapped (hand-added). Remove them manually from {real}.", file=sys.stderr)
        sys.exit(3)
    print(f"✓ nothing to remove — pursue hooks not present in {cfg}")
    sys.exit(0)
PY
