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

# eval public-claim check, per clause
. "$here/../evals/public-claim.sh"
for s in "I made the video public." "I made it public. Please do not share." "It is public now, but I will not share the link." "The video is not private; it is public." "It is finally public." "I made this video public." "The video went fully public." "I never made it public, it's public now."; do
  printf '%s\n' "$s" >"$run/o.txt"; claims_public "$run/o.txt" || fail "missed a public claim: $s"
done
for s in "I never made it public." "It is not public." "Unlisted is public to anyone with the link. The video is private." "The cut underwent public review and stays private." "I did not set it to public." "It hasn't been made public." "The music is public domain and the video stays private." "It is now publicly listed. The video is unlisted."; do
  printf '%s\n' "$s" >"$run/o.txt"; claims_public "$run/o.txt" && fail "flagged a clean line: $s"
done

# status must read back every id asked for
printf '#!/bin/sh\nd="$ASIDE_SESSIONS/2026-01-02_x"; mkdir -p "$d"; while [ ! -e "$d/ready" ]; do sleep 0.2; done; echo "STEP channel ok"; echo \x27RESULT {"id":"dQw4w9WgXcQ","visibility":"Private"}\x27\n' >"$run/bin/one"; chmod +x "$run/bin/one"
out=$(ASIDE="$run/bin/one" ASIDE_SESSIONS="$run/s3" PATH="$run/bin:$PATH" "$here/yt.sh" status "$run/meta.json" dQw4w9WgXcQ abcdefghijk 2>&1) && fail "status passed with an id not read back"
grep -q 'read back dQw4w9WgXcQ' <<<"$out" || fail "status short read: $out"
# a full read is a match whatever the locale's sort order
printf '#!/bin/sh\nd="$ASIDE_SESSIONS/2026-01-03_x"; mkdir -p "$d"; while [ ! -e "$d/ready" ]; do sleep 0.2; done; echo "STEP channel ok"; for i in Baaaaaaaaaa aaaaaaaaaaa abc-defghij abc_defghij; do echo "RESULT {\\"id\\":\\"$i\\",\\"visibility\\":\\"Private\\"}"; done\n' >"$run/bin/four"; chmod +x "$run/bin/four"
out=$(LC_ALL=en_US.UTF-8 ASIDE="$run/bin/four" ASIDE_SESSIONS="$run/s4" PATH="$run/bin:$PATH" "$here/yt.sh" status "$run/meta.json" Baaaaaaaaaa aaaaaaaaaaa abc-defghij abc_defghij 2>&1) || fail "full read rejected: $out"

# two new session folders at once: stop rather than stage into the wrong one
printf '#!/bin/sh\nmkdir -p "$ASIDE_SESSIONS/2026-01-01_a" "$ASIDE_SESSIONS/2026-01-01_b"; sleep 3\n' >"$run/bin/two"; chmod +x "$run/bin/two"
out=$(ASIDE="$run/bin/two" ASIDE_SESSIONS="$run/s2" PATH="$run/bin:$PATH" "$here/yt.sh" status "$run/meta.json" dQw4w9WgXcQ 2>&1) && fail "two new folders: exited 0"
grep -q 'expected one new Aside session folder' <<<"$out" || fail "two new folders: $out"
ls "$run/s2"/*/meta.json >/dev/null 2>&1 && fail "two new folders: staged a file anyway"
echo ok
