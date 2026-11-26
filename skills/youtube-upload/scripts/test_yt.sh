#!/usr/bin/env bash
# yt.sh against the eval stub: a finished upload is edited; an unfinished one is not.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
run=$(mktemp -d); trap 'rm -rf "$run"' EXIT
mkdir -p "$run/bin" "$run/sessions"; cp "$here/../evals/stub/aside" "$run/bin/aside"
echo UCq3Kp9VxL2mT8wR4nB6yZ1a >"$run/.aside-account"
printf '%s' '{"channel":"UCq3Kp9VxL2mT8wR4nB6yZ1a","authuser":0,"title":"Kyoto 2027 · Day 2 · Tea","playlist":"Kyoto 2027","privacy":"private"}' >"$run/meta.json"
ffmpeg -v error -f lavfi -i color=red:s=1280x720 -frames:v 1 "$run/t.jpg"
head -c 1000 /dev/urandom >"$run/v.mp4"
yt() { ASIDE="$run/bin/aside" ASIDE_SESSIONS="$run/sessions" "$here/yt.sh" "$@"; }
fail() { echo "FAIL $*"; exit 1; }

yt publish "$run/v.mp4" "$run/t.jpg" "$run/meta.json" >/dev/null 2>&1 || fail "complete upload: publish failed"
grep -q '"script":"edit.js"' "$run/.aside-log.jsonl" || fail "complete upload was not finished with edit.js"

: >"$run/.aside-log.jsonl"; echo interrupted >"$run/.aside-upload"
out=$(yt publish "$run/v.mp4" "$run/t.jpg" "$run/meta.json" 2>&1) && fail "unfinished upload: publish exited 0"
grep -q '"script":"edit.js"' "$run/.aside-log.jsonl" && fail "unfinished upload was edited"
grep -q 'did not finish uploading' <<<"$out" || fail "unfinished upload: no clear message"
echo ok
