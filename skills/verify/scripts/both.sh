#!/usr/bin/env bash
# Run one proof command on the parent (the merge-base with --base) and on the head, each in a clean temporary
# worktree, and write an evidence manifest. The command must work from a clean checkout, install step included
# (`-- sh -c 'npm ci && npm test'`).
#   both.sh --base <ref> [--head <ref>] --out <manifest.json> [--from-head <path>]... -- <command...>
# --from-head copies a path from the head into the parent checkout first: the new check, run against the old code.
# The manifest records, per side: sha, exit code, seconds, log path (next to the manifest) and log sha256; and an outcome:
#   fixed (parent fails, head passes) | regressed (parent passes, head fails) | same-pass | same-fail.
set -euo pipefail
base="" head="HEAD" out="" from_head=()
while [ $# -gt 0 ]; do
  case "$1" in
    --base) base="$2"; shift 2 ;;
    --head) head="$2"; shift 2 ;;
    --out) out="$2"; shift 2 ;;
    --from-head) from_head+=("$2"); shift 2 ;;
    --) shift; break ;;
    *) echo "both.sh: unknown argument $1 (put the command after --)" >&2; exit 2 ;;
  esac
done
[ -n "$base" ] && [ -n "$out" ] && [ $# -gt 0 ] || { echo "usage: both.sh --base <ref> [--head <ref>] --out <manifest.json> -- <command...>" >&2; exit 2; }
repo=$(git rev-parse --show-toplevel)
parent=$(git merge-base "$base" "$head")
head_sha=$(git rev-parse "$head")
[ "$parent" != "$head_sha" ] || { echo "both.sh: $head is the merge-base itself: nothing changed to verify" >&2; exit 2; }
mkdir -p "$(dirname "$out")"
logs="$(cd "$(dirname "$out")" && pwd -P)/$(basename "$out" .json)-logs"
mkdir -p "$logs"
tmp=$(mktemp -d)
cleanup() { git -C "$repo" worktree remove --force "$tmp/parent" >/dev/null 2>&1 || true; git -C "$repo" worktree remove --force "$tmp/head" >/dev/null 2>&1 || true; rm -rf "$tmp"; }
trap cleanup EXIT
sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }
side() { # name sha -> "exit seconds"
  git -C "$repo" worktree add --detach -q "$tmp/$1" "$2"
  if [ "$1" = parent ]; then
    for p in ${from_head[@]+"${from_head[@]}"}; do
      mkdir -p "$tmp/parent/$(dirname "$p")"
      git -C "$repo" show "$head_sha:$p" > "$tmp/parent/$p" || { echo "both.sh: $p is not in $head_sha" >&2; exit 2; }
    done
  fi
  local start=$SECONDS code=0
  (cd "$tmp/$1" && "${@:3}") >"$logs/$1.log" 2>&1 || code=$?
  echo "$code $((SECONDS - start))"
}
read -r p_exit p_secs < <(side parent "$parent" "$@")
read -r h_exit h_secs < <(side head "$head_sha" "$@")
if [ "$p_exit" != 0 ] && [ "$h_exit" = 0 ]; then outcome=fixed
elif [ "$p_exit" = 0 ] && [ "$h_exit" != 0 ]; then outcome=regressed
elif [ "$p_exit" = 0 ]; then outcome=same-pass
else outcome=same-fail; fi
cmd=$(printf '%q ' "$@")
from=$(printf '%s,' ${from_head[@]+"${from_head[@]}"})
node -e '
const [out, cmd, parent, pe, ps, pl, head, he, hs, hl, outcome, , , from] = process.argv.slice(1);
const side = (sha, exit, secs, log, hash) => ({ sha, exit: Number(exit), seconds: Number(secs), log, log_sha256: hash });
require("fs").writeFileSync(out, JSON.stringify({ schema: "verify.manifest/v1", command: cmd.trim(), outcome,
  from_head: from.split(",").filter(Boolean),
  parent: side(parent, pe, ps, pl, process.argv[12]), head: side(head, he, hs, hl, process.argv[13]),
  recorded_at: new Date().toISOString().replace(/\.\d+Z$/, "Z") }, null, 2) + "\n");
' "$out" "$cmd" "$parent" "$p_exit" "$p_secs" "$(basename "$logs")/parent.log" "$head_sha" "$h_exit" "$h_secs" "$(basename "$logs")/head.log" "$outcome" "$(sha256 "$logs/parent.log")" "$(sha256 "$logs/head.log")" "$from"
echo "$outcome: parent exit $p_exit, head exit $h_exit -> $out"
