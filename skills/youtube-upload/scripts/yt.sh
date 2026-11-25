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
  [[ $channel =~ ^UC[A-Za-z0-9_-]{22}$ ]] || fails+=("channel '$channel' is not a channel id (UC + 22 chars)")
  [ -n "$title" ] || fails+=("no title")
  [ "$(printf %s "$title" | wc -m)" -le 100 ] || fails+=("title over 100 characters")
  [ "$(printf %s "$desc" | wc -m)" -le 5000 ] || fails+=("description over 5000 characters")
  [[ "$title$desc" != *[\<\>]* ]] || fails+=("title or description has < or >, which YouTube rejects")
  case $privacy in private | unlisted) ;; *) fails+=("privacy '$privacy': only private or unlisted; public waits for the owner") ;; esac
  [ -z "$playlist" ] || [ "$(printf %s "$playlist" | wc -m)" -le 150 ] || fails+=("playlist name over 150 characters")
  if [ -s "$thumb" ]; then
    local size dims
    size=$(wc -c <"$thumb" | tr -d ' ')
    [ "$size" -lt 2000000 ] || fails+=("thumbnail is $size bytes; keep it under 2 MB")
    if command -v ffprobe >/dev/null; then
      dims=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x "$thumb" 2>/dev/null || true)
      [ -z "$dims" ] || awk -F x -v d="$dims" '{exit !($1>=640 && $1*9==$2*16)}' <<<"$dims" || fails+=("thumbnail is $dims; use 16:9, at least 640 wide (1280x720)")
    fi
  fi
  if [ ${#fails[@]} -gt 0 ]; then printf 'FAIL %s\n' "${fails[@]}"; return 1; fi
  echo "ok"
}

# Run a repl script with files staged into its session dir: aside repl reads only from that dir, which
# appears when the run starts, so wait for it, copy the files in, then touch 'ready' (the script waits on it).
repl() {
  local js=$1; shift
  local marker out dir="" rp rc=0
  mkdir -p "$ASIDE_SESSIONS"
  marker=$(mktemp); sleep 1
  out=$(mktemp)
  "$ASIDE" repl --file "$here/$js" >"$out" 2>&1 & rp=$!
  for _ in $(seq 1 60); do
    dir=$(find "$ASIDE_SESSIONS" -maxdepth 1 -type d -newer "$marker" -name '20*' | head -1)
    [ -n "$dir" ] && break; sleep 0.5
  done
  rm -f "$marker"
  [ -n "$dir" ] || { kill "$rp" 2>/dev/null; cat "$out" >&2; die "no Aside session dir appeared under $ASIDE_SESSIONS"; }
  while [ $# -gt 1 ]; do cp "$1" "$dir/$2"; shift 2; done
  touch "$dir/ready"
  wait "$rp" || rc=$?
  grep -E '^(STEP|RESULT|Error)' "$out" || cat "$out"
  rm -f "$dir/v.mp4" "$out"
  return "$rc"
}

publish() {
  local video=$1 thumb=$2 meta=$3 up id m
  check "$video" "$thumb" "$meta" || die "fix the FAIL lines first; nothing was uploaded"
  up=$(repl upload.js "$video" v.mp4 "$meta" meta.json) || { echo "$up"; die "upload failed"; }
  echo "$up"
  id=$(sed -n 's/^RESULT //p' <<<"$up" | jq -r '.id // empty')
  [ -n "$id" ] || die "upload gave no video id"
  m=$(mktemp); jq --arg id "$id" '. + {id: $id}' "$meta" >"$m"
  edit "$thumb" "$m"
}

edit() {
  local thumb=$1 meta=$2
  jq -e '.id | strings' "$meta" >/dev/null || die "$meta has no \"id\""
  check none "$thumb" "$meta" || die "fix the FAIL lines first"
  repl edit.js "$thumb" thumb.jpg "$meta" meta.json
  status "$meta" "$(jq -r .id "$meta")"
}

status() {
  local meta=$1; shift
  local m; m=$(mktemp)
  jq --argjson ids "$(printf '%s\n' "$@" | jq -R . | jq -s .)" '. + {ids: $ids}' "$meta" >"$m"
  repl status.js "$m" meta.json
}

cmd=${1:-}; shift || true
case $cmd in
  check) [ $# -eq 3 ] || die "usage: yt.sh check <video> <thumb> <meta.json>"; check "$@" ;;
  publish) [ $# -eq 3 ] || die "usage: yt.sh publish <video> <thumb> <meta.json>"; publish "$@" ;;
  edit) [ $# -eq 2 ] || die "usage: yt.sh edit <thumb> <meta.json>"; edit "$@" ;;
  status) [ $# -ge 2 ] || die "usage: yt.sh status <meta.json> <id>..."; status "$@" ;;
  *) die "usage: yt.sh check|publish|edit|status ..." ;;
esac
