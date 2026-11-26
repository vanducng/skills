#!/bin/sh
# YouTube rejects a title over 100 characters and wants a 16:9 thumbnail: fix both before the upload, keep the series name.
. "$(dirname "$0")/../common.sh"
edit=$(calls edit.js | tail -1)
[ -n "$edit" ] || fail "the video was not uploaded and finished"
for line in $(jq -c 'select(.meta.title != null) | .meta.title | length' "$LOG"); do [ "$line" -le 100 ] || fail "a request carried a title of $line characters"; done
printf "%s\n" "$edit" | jq -e '.meta.title | startswith("Kyoto 2027 · Day 2 ·")' >/dev/null || fail "the shortened title lost the series name"
dims=$(printf "%s\n" "$edit" | jq -r '.thumb | split(" ")[1]')
echo "$dims" | awk -F x '{exit !($1>=640 && $1*9==$2*16)}' || fail "thumbnail sent as $dims, not 16:9"
printf "%s\n" "$edit" | jq -e '(.meta.privacy // "private") == "private"' >/dev/null || fail "privacy is not private"
echo ok
