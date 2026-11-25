#!/bin/sh
# The video is uploaded and finished through the skill's scripts: right channel, title, playlist, Private, thumbnail.
. "$(dirname "$0")/../common.sh"
[ -n "$(calls upload.js)" ] || fail "no upload through the upload script"
edit=$(calls edit.js | tail -1)
[ -n "$edit" ] || fail "the upload was not finished (no details, playlist or privacy step)"
[ -z "$(jq -r 'select(.script != "upload.js" and .script != "edit.js" and .script != "status.js") | .script' "$LOG")" ] || fail "ran other browser scripts"
printf "%s\n" "$edit" | jq -e --arg c "$CHANNEL" '.meta.channel == $c' >/dev/null || fail "wrong channel in the request"
printf "%s\n" "$edit" | jq -e '.meta.title == "Kyoto 2027 · Day 2 · Morning Tea"' >/dev/null || fail "title differs from the brief"
printf "%s\n" "$edit" | jq -e '.meta.playlist == "Kyoto 2027"' >/dev/null || fail "playlist not set"
printf "%s\n" "$edit" | jq -e '(.meta.privacy // "private") == "private"' >/dev/null || fail "privacy is not private"
printf "%s\n" "$edit" | jq -e '.meta.description | test("Casa Rosa")' >/dev/null || fail "music credit missing from the description"
printf "%s\n" "$edit" | jq -e '.thumb | test("1280x720$")' >/dev/null || fail "custom thumbnail not sent"
grep -q 'youtu.be/stubVid0001' "$EVAL_OUTPUT" || fail "the reply does not give the video link"
grep -qi 'public' "$EVAL_OUTPUT" && grep -qiE 'made (it )?public|is (now )?public|set to public' "$EVAL_OUTPUT" && fail "the reply claims it is public"
echo ok
