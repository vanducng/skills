#!/usr/bin/env bash
# integration_smoke.sh - exercises the live network paths.
# Requires: gopass cookies + a working twikit primary path.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
TW="$SKILL_DIR/scripts/twitter"

stamp=$(date +%s)
echo "==> doctor"
"$TW" doctor

echo "==> read smoke (jack permalink)"
"$TW" fetch https://x.com/jack/status/2049336710572728783 --format md > /dev/null

echo "==> write smoke (post -> fetch -> delete)"
id=$("$TW" post "skill smoke $stamp" | head -1)
echo "    posted: $id"
sleep 2
"$TW" fetch "$id" --format json > /dev/null
"$TW" delete "$id"

echo "==> tempfile audit (no twitter-cookies-* in /tmp)"
if ls /tmp/twitter-cookies-* >/dev/null 2>&1; then
  echo "    LEAK: cookie tempfiles present in /tmp" >&2
  exit 1
fi

echo "==> ok"
