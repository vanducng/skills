#!/usr/bin/env bash
# Records a scripted terminal demo with asciinema, optionally drives a TUI through tmux, then scrubs and leak-checks the cast.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: record.sh --session FILE [options] [-- session-args...]
  --session FILE    bash script that runs inside the recording (required)
  --drive FILE      bash script sourced once --ready text is on screen; sends keys with k, lit, wait_for
  --ready TEXT      on-screen text that means the TUI accepts keys (required with --drive)
  --out DIR         output directory (default: $TMPDIR/asciinema-demo)
  --name NAME       cast basename (default: demo)
  --size COLSxROWS  terminal size (default: 120x32)
  --title TEXT      recording title
  --idle SECS       idle time limit, also applied to the GIF (default: 2)
  --timeout SECS    max wait for the recording to finish (default: 300)
  --deny TEXT       extra string that must not appear in the cast (repeatable)
  --gif PATH        also render a GIF with agg
  --theme NAME      agg theme (default: github-dark)
  --font-size N     agg font size (default: 14)
EOF
  exit 2
}

session="" drive="" ready="" out="${TMPDIR:-/tmp}/asciinema-demo" name=demo size=120x32 title="" idle=2
timeout=300 gif="" theme=github-dark font_size=14
deny=() args=()
while (($#)); do
  case $1 in
    --session) session=$2; shift 2 ;;
    --drive) drive=$2; shift 2 ;;
    --ready) ready=$2; shift 2 ;;
    --out) out=$2; shift 2 ;;
    --name) name=$2; shift 2 ;;
    --size) size=$2; shift 2 ;;
    --title) title=$2; shift 2 ;;
    --idle) idle=$2; shift 2 ;;
    --timeout) timeout=$2; shift 2 ;;
    --deny) deny+=("$2"); shift 2 ;;
    --gif) gif=$2; shift 2 ;;
    --theme) theme=$2; shift 2 ;;
    --font-size) font_size=$2; shift 2 ;;
    --) shift; args=("$@"); break ;;
    *) usage ;;
  esac
done
[[ -f $session ]] || { echo "session script not found: ${session:-<none>}" >&2; usage; }
[[ $size =~ ^[0-9]+x[0-9]+$ ]] || { echo "--size must be COLSxROWS" >&2; exit 2; }
[[ -z $drive || -f $drive ]] || { echo "drive script not found: $drive" >&2; exit 2; }
[[ -z $drive || -n $ready ]] || { echo "--drive needs --ready" >&2; exit 2; }
need=(asciinema python3)
[[ -n $drive ]] && need+=(tmux)
[[ -n $gif ]] && need+=(agg)
for tool in "${need[@]}"; do command -v "$tool" >/dev/null || { echo "missing $tool" >&2; exit 1; }; done

session=$(cd "$(dirname "$session")" && pwd)/$(basename "$session")
mkdir -p "$out"
cast="$out/$name.cast"
cmd="bash $(printf '%q' "$session")"
for arg in ${args[@]+"${args[@]}"}; do cmd+=" $(printf '%q' "$arg")"; done
rec=(asciinema rec "$cast" --overwrite --quiet --window-size "$size" --idle-time-limit "$idle")
[[ -n $title ]] && rec+=(--title "$title")
rec+=(--command "$cmd")

if [[ -z $drive ]]; then
  "${rec[@]}" --headless </dev/null
else
  tmux_session="asciinema-rec-$$"
  trap 'tmux kill-session -t "$tmux_session" 2>/dev/null || true' EXIT
  # The command runs with the tmux server's environment, not this shell's, so the session script sets its own env.
  tmux new-session -d -s "$tmux_session" -x "${size%x*}" -y "${size#*x}" "$(printf '%q ' "${rec[@]}")" \; \
    set-option -t "$tmux_session" status off >/dev/null
  # tmux reads a lone ";" argument as a command separator.
  char() { local c=$1; [[ $c == ";" ]] && c='\;'; tmux send-keys -t "$tmux_session" -l -- "$c"; }
  k() {
    local key
    for key in "$@"; do
      if ((${#key} == 1)); then char "$key"; else tmux send-keys -t "$tmux_session" -- "$key"; fi
      sleep "${KEY_DELAY:-0.28}"
    done
  }
  lit() { local s=$1 i; for ((i = 0; i < ${#s}; i++)); do char "${s:i:1}"; sleep "${TYPE_DELAY:-0.07}"; done; }
  wait_for() {
    local text=$1 limit=${2:-30} i
    for ((i = 0; i < limit * 10; i++)); do
      tmux capture-pane -p -t "$tmux_session" 2>/dev/null | grep -qF -- "$text" && return 0
      sleep 0.1
    done
    echo "timed out after ${limit}s waiting for: $text" >&2
    return 1
  }
  wait_for "$ready" "$timeout"
  # shellcheck source=/dev/null
  (source "$drive")
  for ((i = 0; i < timeout * 10; i++)); do tmux has-session -t "$tmux_session" 2>/dev/null || break; sleep 0.1; done
  tmux has-session -t "$tmux_session" 2>/dev/null && { echo "recording still running after ${timeout}s" >&2; exit 1; }
fi
[[ -s $cast ]] || { echo "no cast written: $cast" >&2; exit 1; }

python3 - "$cast" "$(basename "$session")" ${deny[@]+"${deny[@]}"} <<'PY'
import json, os, re, sys

path, shown, *deny = sys.argv[1:]
lines = open(path, encoding="utf-8").read().splitlines()
header = json.loads(lines[0])
header["command"] = f"bash {shown}"
lines[0] = json.dumps(header)
open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")

parts = [lines[0]]
for raw in lines[1:]:
    if raw.strip() and not raw.startswith("#"):
        parts.append(str(json.loads(raw)[2]))
text = "\n".join(parts)
text += "\n" + re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", text)
checks = {"home directory": os.path.expanduser("~"), "/Users/ path": "/Users/", "/home/ path": "/home/",
          "loopback address": "127.0.0.1", "localhost port": "localhost:", "access_token": "access_token",
          "refresh_token": "refresh_token", "bearer header": "Bearer "}
checks.update({f"--deny #{i}": d for i, d in enumerate(deny, 1)})
found = [label for label, needle in checks.items() if needle and needle in text]
if found:
    sys.exit(f"private data in the cast ({', '.join(found)}); do not upload {path}")
PY

if [[ -n $gif ]]; then
  mkdir -p "$(dirname "$gif")"
  agg --font-size "$font_size" --idle-time-limit "$idle" --fps-cap 15 --last-frame-duration 3 --theme "$theme" \
    "$cast" "$gif" >/dev/null 2>&1 || { echo "agg failed for $cast" >&2; exit 1; }
  echo "gif=$gif"
fi
echo "cast=$cast"
