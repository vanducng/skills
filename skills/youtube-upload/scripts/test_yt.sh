#!/usr/bin/env bash
# yt.sh against the eval stub: a finished upload is edited; an unfinished one is not.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
run=$(mktemp -d); trap 'rm -rf "$run"' EXIT
mkdir -p "$run/bin" "$run/sessions"; cp "$here/../evals/stub/aside" "$run/bin/aside"
echo UCq3Kp9VxL2mT8wR4nB6yZ1a >"$run/.aside-account"
printf '%s' '{"channel":"UCq3Kp9VxL2mT8wR4nB6yZ1a","authuser":0,"title":"Kyoto 2027 · Day 2 · Tea","playlist":"Kyoto 2027","privacy":"private"}' >"$run/meta.json"
# a stand-in ffprobe, so the test needs no ffmpeg: every image reads as 1280x720
printf '#!/bin/sh\necho 1280x720\n' >"$run/bin/ffprobe"; chmod +x "$run/bin/ffprobe"
head -c 2000 /dev/urandom >"$run/t.jpg"
head -c 1000 /dev/urandom >"$run/v.mp4"
yt() { PATH="$run/bin:$PATH" ASIDE="$run/bin/aside" ASIDE_SESSIONS="$run/sessions" "$here/yt.sh" "$@"; }
fail() { echo "FAIL $*"; exit 1; }

yt publish "$run/v.mp4" "$run/t.jpg" "$run/meta.json" >/dev/null 2>&1 || fail "complete upload: publish failed"
grep -q '"script":"edit.js"' "$run/.aside-log.jsonl" || fail "complete upload was not finished with edit.js"

: >"$run/.aside-log.jsonl"; echo interrupted >"$run/.aside-upload"
out=$(yt publish "$run/v.mp4" "$run/t.jpg" "$run/meta.json" 2>&1) && fail "unfinished upload: publish exited 0"
grep -q '"script":"edit.js"' "$run/.aside-log.jsonl" && fail "unfinished upload was edited"
grep -q 'did not finish uploading' <<<"$out" || fail "unfinished upload: no clear message"

# two new session folders at once: stop rather than stage into the wrong one
printf '#!/bin/sh\nmkdir -p "$ASIDE_SESSIONS/2026-01-01_a" "$ASIDE_SESSIONS/2026-01-01_b"; sleep 3\n' >"$run/bin/two"; chmod +x "$run/bin/two"
out=$(ASIDE="$run/bin/two" ASIDE_SESSIONS="$run/s2" PATH="$run/bin:$PATH" "$here/yt.sh" status "$run/meta.json" dQw4w9WgXcQ 2>&1) && fail "two new folders: exited 0"
grep -q 'expected one new Aside session folder' <<<"$out" || fail "two new folders: $out"
ls "$run/s2"/*/meta.json >/dev/null 2>&1 && fail "two new folders: staged a file anyway"
echo ok
