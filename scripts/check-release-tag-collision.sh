#!/usr/bin/env bash
# Fail when version.txt is behind an existing v* tag on origin.
# Catches the class of bug where release-please was reset to 1.0.0 while
# historical tags v1.0.0-v1.53.1 still existed, so GitHub Releases fail with
# tag_name already_exists.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "${REPO}/version.txt")"

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+ ]]; then
  echo "check-release-tag-collision: version.txt is not SemVer: ${VERSION}" >&2
  exit 1
fi

# Prefer origin (CI + local clones). Fall back to local tags when offline.
if tags="$(git -C "$REPO" ls-remote --tags origin 'v*' 2>/dev/null)"; then
  :
else
  tags="$(git -C "$REPO" tag -l 'v*')"
fi

latest="$(
  printf '%s\n' "$tags" \
    | awk '{print $NF}' \
    | sed 's|refs/tags/||' \
    | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' \
    | sort -t. -k1,1 -k2,2n -k3,3n \
    | tail -1
)"

if [[ -z "$latest" ]]; then
  echo "OK no existing v* tags (version ${VERSION})"
  exit 0
fi

latest_bare="${latest#v}"

python3 - "$VERSION" "$latest_bare" <<'PY'
import sys

def parse(v):
    core = v.split("-", 1)[0]
    parts = core.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise SystemExit(f"not SemVer: {v}")
    return tuple(int(p) for p in parts)

current, latest = sys.argv[1], sys.argv[2]
if parse(current) < parse(latest):
    print(
        f"check-release-tag-collision: version.txt {current} is behind "
        f"existing tag v{latest}. GitHub will reject the next release "
        f"(tag_name already_exists). Bump past v{latest}.",
        file=sys.stderr,
    )
    sys.exit(1)
print(f"OK version {current} is not behind existing tag v{latest}")
PY
