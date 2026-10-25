#!/usr/bin/env bash
# Runs inside `asciinema rec`: silent setup, then each command typed on screen. Copy, then edit SETUP and SCENES.
set -u

# SETUP: everything here is in the cast, so keep it silent and point the tool at sample data, never a real account.
# export XDG_CONFIG_HOME="$1/cfg" PATH="$2:$PATH"

note() { printf '\033[2m# %s\033[0m\n' "$1"; sleep "${2:-0.6}"; }
run() {
  printf '\033[1;32m$\033[0m '
  local s=$1 i
  for ((i = 0; i < ${#s}; i++)); do printf '%s' "${s:i:1}"; sleep 0.02; done
  sleep 0.35
  printf '\n'
  eval "$s"
  sleep "${2:-1.8}"
}

clear
# SCENES: one note per scene, clear between scenes. A TUI scene ends when the drive script quits it.
note "mytool: what it does in one line"
run "mytool --help | head -12" 3
clear
note "Install: <where to get it>"
sleep 2
