#!/usr/bin/env bash
# Compact, read-only status for a tracked initiative: the data behind each periodic brief.
#   status.sh --rig <rig> --project-dir <dir> --missions <m1,m2> [--repo <owner/repo>] [--search "<gh search>"] [--since <ISO>]
# Prints: time, host health (when fleet/bin/host-health exists), seat activity, queue rows the rig created
# since --since, the last PROGRESS line of every slice, and matching PRs.
set -euo pipefail

rig="" dir="" missions="" repo="" search="" since=""
while [ $# -gt 0 ]; do
  case "$1" in
    --rig) rig="$2"; shift 2 ;;
    --project-dir) dir="$2"; shift 2 ;;
    --missions) missions="$2"; shift 2 ;;
    --repo) repo="$2"; shift 2 ;;
    --search) search="$2"; shift 2 ;;
    --since) since="$2"; shift 2 ;;
    *) echo "status: unknown flag $1" >&2; exit 2 ;;
  esac
done
[ -n "$rig" ] && [ -n "$dir" ] && [ -n "$missions" ] || { echo "status: --rig, --project-dir and --missions are required" >&2; exit 2; }
since="${since:-$(date -u -v-12H '+%Y-%m-%dT%H:%M' 2>/dev/null || date -u -d '12 hours ago' '+%Y-%m-%dT%H:%M')}"

echo "now: $(date '+%H:%M %Z') / $(date -u '+%H:%MZ')"
hh="${PROJECTS_ROOT:-$HOME/projects}/fleet/bin/host-health"
[ -x "$hh" ] && { echo "== host"; "$hh" 2>&1 | tail -1; }
echo "== seats"; rig ps --nodes --rig "$rig" 2>/dev/null | awk -v r="$rig" 'NR>1 && $1==r {print $2, $4, "work="$5}'
echo "== rows from $rig since $since"
rig queue list -A --json 2>/dev/null | jq -r --arg s "$since" --arg r "@$rig" \
  '.[] | select(.tsCreated > $s) | select(.sourceSession | endswith($r)) | [.tsCreated[11:16], .sourceSession, .destinationSession, .state, .summary[0:150]] | @tsv' | tail -15
for m in ${missions//,/ }; do
  echo "== $m"
  [ -d "$dir/missions/$m/slices" ] || { echo "(no mission dir)"; continue; }
  for s in "$dir/missions/$m/slices"/*/; do
    last="$(grep -E '^- ' "$s/PROGRESS.md" 2>/dev/null | tail -1 | cut -c1-170 || true)"
    echo "$(basename "$s") | ${last:-no progress line}"
  done
done
if [ -n "$repo" ] && [ -n "$search" ]; then
  echo "== PRs"
  gh pr list -R "$repo" --state all --search "$search" --json number,state,updatedAt,title \
    --jq '.[] | [.number, .state, .updatedAt[11:16], .title[0:90]] | @tsv' 2>/dev/null | head -10
fi
