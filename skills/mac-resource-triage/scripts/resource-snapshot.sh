#!/usr/bin/env bash
# Read-only snapshot of a macOS workstation: load vs cores, memory pressure, swap, CPU split,
# consumers grouped by app bundle, the run queue, process counts, and container stats.
# Usage: resource-snapshot.sh [top_n]
set -euo pipefail

# top's MEM is the physical footprint: resident plus compressed plus swapped pages. RSS misses a process whose
# pages sit in the compressor or swap (a daemon at 2 GB RSS can hold 39 GB). Reads "pid mem cmprs" rows ($1)
# and "pid comm" rows ($2); prints footprint MB, compressed MB, process count, app.
footprint_by_app() {
  awk 'function mb(s,  u, v) { sub(/[+-]$/, "", s); u = substr(s, length(s)); v = substr(s, 1, length(s) - 1) + 0
         return u == "G" ? v * 1024 : u == "M" ? v : u == "K" ? v / 1024 : v / 1048576 }
    NR == FNR { pid = $1; $1 = ""; n = $0; sub(/^ +/, "", n); sub(/\.app\/.*/, ".app", n); sub(/.*\//, "", n); A[pid] = n; next }
    ($1 in A) { k = A[$1]; F[k] += mb($2); Z[k] += mb($3); N[k]++ }
    END { for (k in F) printf "%7.0f MB %7.0f MB %5d  %s\n", F[k], Z[k], N[k], k }' "$2" "$1"
}
[[ "${BASH_SOURCE[0]}" == "$0" ]] || return 0

top_n="${1:-12}"
[[ "$top_n" =~ ^[1-9][0-9]*$ ]] || { echo "usage: $0 [top_n >= 1]" >&2; exit 1; }
[[ "$(uname -s)" == Darwin ]] || { echo "macOS only" >&2; exit 1; }

cores="$(sysctl -n hw.ncpu)"
ram_gb="$(( $(sysctl -n hw.memsize) / 1073741824 ))"
echo "== host $(scutil --get LocalHostName 2>/dev/null || hostname)  cores=${cores}  ram=${ram_gb}G"
uptime
echo "swap: $(sysctl -n vm.swapusage)"
memory_pressure 2>/dev/null | tail -1 || true
# The first top sample has no CPU delta; print only the second.
top -l 2 -n 0 -s 2 | awk '/^Processes:/ { n++ } n == 2 && /^(Processes|CPU usage|PhysMem)/'

# Browsers and Electron apps run dozens of helpers; group them under their .app bundle.
ps_rows="$(ps -Ao rss=,pcpu=,comm=)"
by_app() {
  awk '{
    r = $1; c = $2; $1 = ""; $2 = ""; n = $0
    sub(/^ +/, "", n); sub(/\.app\/.*/, ".app", n); sub(/.*\//, "", n)
    R[n] += r; C[n] += c; N[n]++
  } END { for (k in R) printf "%7.0f MB %7.1f%% %5d  %s\n", R[k] / 1024, C[k], N[k], k }' <<<"$ps_rows"
}

app_rows="$(by_app)"
echo
echo "== top by CPU (RSS, CPU%, procs, app)"
sort -k3 -rn <<<"$app_rows" | awk -v n="$top_n" 'NR <= n'
echo
echo "== top by memory footprint (MB incl. compressed and swapped, of which compressed, procs, app)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
top -l 1 -o mem -n 300 -stats pid,mem,cmprs | awk 'f && NF == 3; $1 == "PID" { f = 1 }' >"$tmp/top"
ps -Ao pid=,comm= >"$tmp/ps"
footprint_by_app "$tmp/top" "$tmp/ps" | sort -k1 -rn | awk -v n="$top_n" 'NR <= n'

# macOS load average counts runnable threads (state R); U is uninterruptible wait, not in load.
echo
echo "== run queue now (R = runnable, U = uninterruptible wait)"
ps -Ao state=,comm= | awk '$1 ~ /^[RU]/ { s = substr($1, 1, 1); $1 = ""; n = $0; sub(/^ +/, "", n); sub(/.*\//, "", n); print s, n }' |
  sort | uniq -c | sort -rn | awk -v n="$top_n" 'NR <= n'

echo
echo "== process counts (machine-wide, not only agents)"
count() { pgrep "$@" 2>/dev/null | wc -l | tr -d ' '; }
# Native Claude installs run as .../claude/versions/<ver>; Python shows as Python or python3.x.
printf '%-9s %s\n' claude "$(count -f '^([^ ]*/)?claude( |$)|^[^ ]*/claude/versions/')"
printf '%-9s %s\n' python "$(count -if '(^|/)python[0-9.]*( |$)')"
for name in codex node uv jump-cli zsh -zsh tmux; do
  printf '%-9s %s\n' "$name" "$(count -x -- "$name")"
done

if command -v docker >/dev/null 2>&1 && docker ps -q >/dev/null 2>&1; then
  echo
  echo "== containers by CPU ($(docker ps -q | wc -l | tr -d ' ') running)"
  docker stats --no-stream --format '{{.CPUPerc}}\t{{.MemUsage}}\t{{.Name}}' | sort -rn | awk -v n="$top_n" 'NR <= n'
fi
