#!/usr/bin/env bash
# Two questions become two decision cards, each with its own lettered options and one recommendation.
set -u
. "$(dirname "$0")/../common-checks.sh"
[ "$(cards)" = 2 ] || { echo "want 2 decision cards, found $(cards)"; exit 1; }
card_ok || exit 1
grep -q 'https://ci.example.com/team/overview' message.md || { echo "the dashboard is not linked"; exit 1; }
echo ok
