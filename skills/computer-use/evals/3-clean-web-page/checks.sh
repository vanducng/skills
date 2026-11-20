#!/usr/bin/env bash
set -u
! grep -q 'agent-desktop' "$EVAL_OUTPUT" || { echo "drove a web page through the desktop"; exit 1; }
