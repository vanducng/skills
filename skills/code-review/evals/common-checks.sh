# Sourced by each scenario's checks.sh. The verdict must sit at record/proof/review.md and bind to main..feat.
set -u
v=record/proof/review.md
[ -f "$v" ] || { echo "no verdict at $v"; exit 1; }
field() { sed -n '/^---$/,/^---$/p' "$v" | grep -m1 "^$1:" | sed "s/^$1: *//; s/^\"//; s/\"$//"; }
axis() { field axes | tr -d '{}' | tr ',' '\n' | sed 's/^ *//' | grep "^$1:" | sed "s/^$1: *//"; }
base=$(git merge-base main feat) || { echo "repo is gone"; exit 1; }
want_patch=$(git diff "$base..feat" | git patch-id --stable | cut -d' ' -f1)
sha() { if command -v sha256sum >/dev/null; then sha256sum; else shasum -a 256; fi; }
want_digest="sha256:$(git diff --binary "$base..feat" | sha | cut -d' ' -f1)"
[ "$(field patch_id)" = "$want_patch" ] || { echo "patch_id does not bind to main..feat"; exit 1; }
[ "$(field diff_digest)" = "$want_digest" ] || { echo "diff_digest does not bind to main..feat"; exit 1; }
[ "$(git rev-parse feat)" = "$(cat .feat-head)" ] || { echo "the reviewer changed the branch"; exit 1; }
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "the reviewer edited tracked files"; exit 1; }
[ ! -e calls.log ] || { echo "the reviewer delegated: $(head -1 calls.log)"; exit 1; }
open_important() { sed -n '/^findings:/,/^---$/p' "$v" | grep -E "axis: \"?$1\"?" | grep -E 'tag: "?Important' | grep -cE 'status: "?open'; }
