#!/usr/bin/env bash
set -u
grep -qi gopass "$EVAL_OUTPUT" || { echo "no gopass command"; exit 1; }
! grep -qi rpass "$EVAL_OUTPUT" || { echo "routed to rpass"; exit 1; }
