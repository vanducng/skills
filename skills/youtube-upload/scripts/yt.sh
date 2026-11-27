#!/usr/bin/env bash
# yt.sh: upload and finish YouTube videos through Aside (the owner's signed-in browser).
#
#   yt.sh check   <video.mp4> <thumb.jpg> <meta.json>   validate files and metadata, change nothing
#   yt.sh publish <video.mp4> <thumb.jpg> <meta.json>   check, upload, then set details, playlist and privacy
#   yt.sh edit    <thumb.jpg> <meta.json>               finish an uploaded video (meta.json has "id")
#   yt.sh status  <meta.json> <id>...                   read back title, privacy, playlist, thumbnail
#
# meta.json: {"channel": "UC...", "authuser": 1, "title": "...", "description": "...",
#             "playlist": "...", "privacy": "private" | "unlisted"}
# Env: ASIDE (default aside), ASIDE_SESSIONS (default ~/.aside/u/0/sessions).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
ASIDE=${ASIDE:-aside}
ASIDE_SESSIONS=${ASIDE_SESSIONS:-$HOME/.aside/u/0/sessions}

die() { echo "yt: $*" >&2; exit 2; }

check() {
  local video=$1 thumb=$2 meta=$3 fails=()
  [ -f "$meta" ] || die "no meta file $meta"
  jq -e . "$meta" >/dev/null 2>&1 || die "$meta is not JSON"
  [ "$video" = none ] || [ -s "$video" ] || fails+=("video $video missing or empty")
  [ -s "$thumb" ] || fails+=("thumbnail $thumb missing or empty")
  local channel title desc privacy playlist
  channel=$(jq -r '.channel // ""' "$meta"); title=$(jq -r '.title // ""' "$meta")
  desc=$(jq -r '.description // ""' "$meta"); privacy=$(jq -r '.privacy // "private"' "$meta")
  playlist=$(jq -r '.playlist // ""' "$meta")
  [[ $(jq -r '.authuser // 0' "$meta") =~ ^[0-9]+$ ]] || fails+=("authuser must be a whole number (the Google account index)")
  [[ $channel =~ ^UC[A-Za-z0-9_-]{22}$ ]] || fails+=("channel '$channel' is not a channel id (UC + 22 chars)")
  [ -n "$title" ] || fails+=("no title")
  [ "$(jq '.title // "" | length' "$meta")" -le 100 ] || fails+=("title over 100 characters")
  [ "$(jq '.description // "" | length' "$meta")" -le 5000 ] || fails+=("description over 5000 characters")
  [[ "$title$desc" != *[\<\>]* ]] || fails+=("title or description has < or >, which YouTube rejects")
  case "$privacy" in private | unlisted) ;; *) fails+=("privacy '$privacy': only private or unlisted; public waits for the owner") ;; esac
  [ -z "$playlist" ] || [ "$(jq '.playlist | length' "$meta")" -le 150 ] || fails+=("playlist name over 150 characters")
  if [ -s "$thumb" ]; then
    local size dims
    size=$(wc -c <"$thumb" | tr -d ' ')
    [ "$size" -lt 2000000 ] || fails+=("thumbnail is $size bytes; keep it under 2 MB")
    dims=""
    command -v ffprobe >/dev/null && dims=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x "$thumb" 2>/dev/null || true)
    if [ -z "$dims" ]; then fails+=("could not read the thumbnail size (is ffprobe installed?)")
    else awk -F x '{exit !($1>=640 && $1*9==$2*16)}' <<<"$dims" || fails+=("thumbnail is $dims; use 16:9, at least 640 wide (1280x720)"); fi
  fi
  if [ ${#fails[@]} -gt 0 ]; then printf 'FAIL %s\n' "${fails[@]}"; return 1; fi
  echo "ok"
}

# Run a repl script with files staged into its session dir: aside repl reads only from that dir, which
# appears when the run starts, so wait for it, copy the files in, then touch 'ready' (the script waits on it).
repl() {
  local js=$1; shift
  local out dir="" rp rc=0 before new staged=()
  mkdir -p "$ASIDE_SESSIONS"
  dirs() { find "$ASIDE_SESSIONS" -mindepth 1 -maxdepth 1 -type d | sed 's#.*/##' | sort; }
  before=$(dirs)
  out=$(mktemp)
  "$ASIDE" repl --file "$here/$js" >"$out" 2>&1 & rp=$!
  # The run's folder is the one session folder that was not there before; with two new ones, stop rather than guess.
  for _ in $(seq 1 60); do
    new=$(comm -13 <(echo "$before") <(dirs))
    [ "$(grep -c . <<<"$new")" -gt 1 ] && break
    # take it only when a second look, a moment later, still finds that one folder and no other
    [ -n "$new" ] && { sleep 0.5; [ "$(comm -13 <(echo "$before") <(dirs))" = "$new" ] && [ -d "$ASIDE_SESSIONS/$new" ] && break; }
    new=""
    sleep 0.5
  done
  [ "$(grep -c . <<<"$new")" -eq 1 ] || { kill "$rp" 2>/dev/null; cat "$out" >&2; rm -f "$out" ${staged[@]+"${staged[@]}"}; die "expected one new Aside session folder under $ASIDE_SESSIONS, found: $(paste -sd , - <<<"${new:-none}")"; }
  dir="$ASIDE_SESSIONS/$new"
  [ -d "$dir" ] || { kill "$rp" 2>/dev/null; rm -f "$out" ${staged[@]+"${staged[@]}"}; die "$dir is not a folder"; }
  while [ $# -gt 1 ]; do
    cp "$1" "$dir/$2" || { kill "$rp" 2>/dev/null; rm -f "$out" "$dir/$2" ${staged[@]+"${staged[@]}"}; die "could not stage $1"; }
    staged+=("$dir/$2"); shift 2
  done
  touch "$dir/ready"
  wait "$rp" || rc=$?
  if [ "$rc" -ne 0 ]; then cat "$out"; else grep -E '^(STEP|RESULT|Error)' "$out" || cat "$out"; fi
  rm -f "${staged[@]}" "$dir/ready" "$out"
  return "$rc"
}

publish() {
  local video=$1 thumb=$2 meta=$3 up id m
  check "$video" "$thumb" "$meta" || die "fix the FAIL lines first; nothing was uploaded"
  up=$(repl upload.js "$video" v.mp4 "$meta" meta.json) || true
  echo "$up"
  id=$(sed -n 's/^RESULT //p' <<<"$up" | jq -r '.id // empty')
  grep -q '^STEP file handed over' <<<"$up" || die "nothing was uploaded; fix the error above and run publish again"
  [ -n "$id" ] || die "upload gave no video id. The file was handed to YouTube and may have arrived: look for a new draft on the channel and finish it with 'yt.sh edit' (add its id); do not upload again"
  grep -q '^STEP upload complete' <<<"$up" || die "video $id did not finish uploading and shows \"Upload interrupted\" in Studio. Do not edit it. Tell the owner; a new upload makes a second copy, and only the owner deletes the broken one"
  m=$(mktemp); jq --arg id "$id" '. + {id: $id}' "$meta" >"$m"
  # A video edited seconds after its upload can stay a draft (seen twice live); a second edit finishes it.
  (edit "$thumb" "$m") && return 0
  echo "yt: $id is not finished yet; editing it once more" >&2
  sleep "${YT_RETRY_WAIT:-20}"; edit "$thumb" "$m"
}

edit() {
  local thumb=$1 meta=$2
  jq -e '.id | strings | test("^[A-Za-z0-9_-]{11}$")' "$meta" >/dev/null || die "$meta has no video \"id\" (11 characters)"
  check none "$thumb" "$meta" || die "fix the FAIL lines first"
  repl edit.js "$thumb" thumb.jpg "$meta" meta.json
  status "$meta" "$(jq -r .id "$meta")"
}

status() {
  local meta=$1; shift
  local m; m=$(mktemp)
  jq --argjson ids "$(printf '%s\n' "$@" | jq -R . | jq -s .)" '. + {ids: $ids}' "$meta" >"$m"
  local out; out=$(repl status.js "$m" meta.json) || { echo "$out"; die "status failed"; }
  echo "$out"
  ! grep -q '"visibility":"Public"' <<<"$out" || die "a video reads back as Public; tell the owner now"
  local want; want=$(jq -r '(.privacy // "private") | ascii_downcase' "$meta")
  # Pending: YouTube's checks have not run; the chosen privacy applies after them.
  local bad got
  got=$(sed -n 's/^RESULT //p' <<<"$out" | jq -rs '[.[].id] | sort | join(" ")' 2>/dev/null) || die "could not read the status output"
  local asked; asked=$(printf '%s\n' "$@" | jq -Rrs '[split("\n")[] | select(length > 0)] | sort | join(" ")')
  [ "$got" = "$asked" ] || die "could not read the status output: asked for $asked, read back ${got:-nothing}"
  sed -n 's/^RESULT //p' <<<"$out" | jq -e -s 'all(.visibility | type == "string")' >/dev/null || die "could not read the status output: a result has no visibility"
  bad=$(sed -n 's/^RESULT //p' <<<"$out" | jq -r --arg w "$want" \
    'if (.visibility | ascii_downcase) != $w and .visibility != "Pending" then "\(.id) is \(.visibility)" else empty end') \
    || die "could not read the status output"
  [ -z "$bad" ] || die "read-back differs from $want: $bad; finish it in Studio or tell the owner"
  return 0
}

cmd=${1:-}; shift || true
case $cmd in
  check) [ $# -eq 3 ] || die "usage: yt.sh check <video> <thumb> <meta.json>"; check "$@" ;;
  publish) [ $# -eq 3 ] || die "usage: yt.sh publish <video> <thumb> <meta.json>"; publish "$@" ;;
  edit) [ $# -eq 2 ] || die "usage: yt.sh edit <thumb> <meta.json>"; edit "$@" ;;
  status) [ $# -ge 2 ] || die "usage: yt.sh status <meta.json> <id>..."; status "$@" ;;
  *) die "usage: yt.sh check|publish|edit|status ..." ;;
esac
