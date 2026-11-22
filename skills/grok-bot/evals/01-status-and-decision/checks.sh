#!/usr/bin/env bash
# A short status, the PR as a link, no local paths, one decision card with lettered options and one recommendation.
set -u
. "$(dirname "$0")/../common-checks.sh"
[ "$(cards)" = 1 ] || { echo "want 1 decision card (**Decision 1: ...?**), found $(cards)"; exit 1; }
card_ok || exit 1
grep -q 'https://github.com/example/shop/pull/481' message.md || { echo "the PR is not linked"; exit 1; }
w=$(wc -w < message.md | tr -d ' '); [ "$w" -le 220 ] || { echo "message is $w words, want 220 or fewer"; exit 1; }
echo ok
