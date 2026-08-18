#!/usr/bin/env bash
# Tests for wait-for-checks.sh. Run: bash skills/git/scripts/wait-for-checks.test.sh
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$DIR/wait-for-checks.sh"
pass=0
fail=0
ok()  { pass=$((pass+1)); echo "  ✓ $1"; }
bad() { fail=$((fail+1)); echo "  ✗ $1"; }
assert_exit() {
  local want="$1" desc="$2"
  shift 2
  "$@" >/dev/null 2>&1
  local got=$?
  if [[ "$got" == "$want" ]]; then
    ok "$desc"
  else
    bad "$desc (exit $got, want $want)"
  fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
BIN="$TMP/bin"
mkdir -p "$BIN"
STATE="$TMP/state"

write_gh() {
  cat > "$BIN/gh" <<EOF
#!/usr/bin/env bash
state_file="$STATE"
mode="\$WAIT_FOR_CHECKS_FAKE_MODE"
n=\$(cat "\$state_file" 2>/dev/null || echo 0)
n=\$((n+1))
echo "\$n" > "\$state_file"
echo "gh-args:\$*"
case "\$mode" in
  pass-after-pending)
    if [[ "\$n" -lt 3 ]]; then
      echo "validate	pending"
      exit 8
    fi
    echo "validate	pass"
    exit 0
    ;;
  always-pending)
    echo "validate	pending"
    exit 8
    ;;
  fail)
    echo "validate	fail"
    exit 1
    ;;
  boom)
    echo "GraphQL: Something went wrong (HTTP 503)" >&2
    exit 1
    ;;
  *)
    echo "unexpected fake mode: \$mode" >&2
    exit 99
    ;;
esac
EOF
  chmod +x "$BIN/gh"
}

write_gh
export PATH="$BIN:$PATH"

echo "wait-for-checks tests:"

: > "$STATE"
assert_exit 0 "pending then pass → exit 0" \
  env WAIT_FOR_CHECKS_FAKE_MODE=pass-after-pending \
  bash "$RUNNER" 12 --timeout 30 --interval 0

: > "$STATE"
assert_exit 1 "fail is terminal (no retry)" \
  env WAIT_FOR_CHECKS_FAKE_MODE=fail \
  bash "$RUNNER" 12 --timeout 30 --interval 0

: > "$STATE"
assert_exit 1 "HTTP 503 is terminal (no retry/backoff)" \
  env WAIT_FOR_CHECKS_FAKE_MODE=boom \
  bash "$RUNNER" 12 --timeout 30 --interval 0

: > "$STATE"
assert_exit 8 "still pending after timeout → exit 8" \
  env WAIT_FOR_CHECKS_FAKE_MODE=always-pending \
  bash "$RUNNER" 12 --timeout 0 --interval 0

assert_exit 2 "unknown flag → exit 2" \
  bash "$RUNNER" --not-a-flag

assert_exit 2 "bad timeout → exit 2" \
  bash "$RUNNER" --timeout nope

# --required is forwarded to gh
: > "$STATE"
out=$(WAIT_FOR_CHECKS_FAKE_MODE=fail bash "$RUNNER" 44 --required --timeout 5 --interval 0 2>&1 || true)
if printf '%s\n' "$out" | grep -q -- '--required'; then
  ok "--required forwarded to gh"
else
  bad "--required not forwarded (output: $out)"
fi

# pending→pass must have polled more than once
: > "$STATE"
WAIT_FOR_CHECKS_FAKE_MODE=pass-after-pending bash "$RUNNER" 12 --timeout 30 --interval 0 >/dev/null 2>&1 || true
calls=$(cat "$STATE")
if [[ "$calls" -ge 3 ]]; then
  ok "exit 8 retried until pass ($calls polls)"
else
  bad "exit 8 did not retry (polls=$calls, want >=3)"
fi

# fail must not be retried
: > "$STATE"
WAIT_FOR_CHECKS_FAKE_MODE=fail bash "$RUNNER" 12 --timeout 30 --interval 0 >/dev/null 2>&1 || true
calls=$(cat "$STATE")
if [[ "$calls" -eq 1 ]]; then
  ok "non-8 failure polled once"
else
  bad "non-8 failure retried (polls=$calls, want 1)"
fi

# missing gh: PATH with no gh binary (system /bin/gh is real in this image)
MIN="$TMP/minimal"
mkdir -p "$MIN"
ln -s /usr/bin/sleep "$MIN/sleep"
assert_exit 2 "gh missing → exit 2" \
  env PATH="$MIN" /usr/bin/bash "$RUNNER" 12

echo
echo "summary: pass=$pass fail=$fail"
[[ "$fail" -eq 0 ]]
