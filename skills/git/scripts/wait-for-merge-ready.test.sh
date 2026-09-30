#!/usr/bin/env bash
# Tests for wait-for-merge-ready.sh. Run: bash skills/git/scripts/wait-for-merge-ready.test.sh
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$DIR/wait-for-merge-ready.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
fail=0

# Fake gh: FAKE_SEQ is a space-separated list of "state|review|merge|unresolved", one per poll.
cat > "$TMP/bin/gh" <<'GH'
#!/usr/bin/env bash
n=$(cat "$TMP_STATE" 2>/dev/null || echo 0)
read -ra seq <<<"$FAKE_SEQ"
i=$(( n < ${#seq[@]} ? n : ${#seq[@]} - 1 ))
IFS='|' read -r state review merge unresolved <<<"${seq[$i]}"
if [[ "$1" == "pr" ]]; then
  printf '7|%s|%s|%s|https://github.com/o/r/pull/7\n' "$state" "$review" "$merge"
else
  echo "$unresolved"; echo $((n + 1)) > "$TMP_STATE"
fi
GH
chmod +x "$TMP/bin/gh"

check() {
  local want="$1" desc="$2" seq="$3"
  shift 3
  rm -f "$TMP/state"
  PATH="$TMP/bin:$PATH" TMP_STATE="$TMP/state" FAKE_SEQ="$seq" "$RUNNER" 7 --interval 0 --timeout 5 "$@" >/dev/null 2>&1
  local got=$?
  if [[ "$got" == "$want" ]]; then echo "  ✓ $desc"; else echo "  ✗ $desc (exit $got, want $want)"; fail=1; fi
}

check 0 "waits through a required approval, then reports ready" "OPEN|REVIEW_REQUIRED|BLOCKED|0 OPEN|APPROVED|CLEAN|0"
check 0 "ready without a review requirement" "OPEN||CLEAN|0"
check 4 "stops when a review thread opens" "OPEN|REVIEW_REQUIRED|BLOCKED|0 OPEN|REVIEW_REQUIRED|BLOCKED|1"
check 4 "stops on changes requested" "OPEN|CHANGES_REQUESTED|BLOCKED|0"
check 4 "stops on a merge conflict" "OPEN|APPROVED|DIRTY|0"
check 3 "reports a PR merged elsewhere" "MERGED|APPROVED|UNKNOWN|0"
check 8 "times out while still blocked" "OPEN|REVIEW_REQUIRED|BLOCKED|0"
check 2 "rejects a bad flag" "OPEN||CLEAN|0" --bogus
exit "$fail"
