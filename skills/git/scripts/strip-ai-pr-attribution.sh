#!/usr/bin/env bash
# Strip AI attribution footers Cursor/Claude may inject into a PR body.
# Usage: strip-ai-pr-attribution.sh [PR_NUMBER] [OWNER/REPO]
set -euo pipefail

pr="${1:-}"
repo="${2:-}"

repo_args=()
if [[ -n "$repo" ]]; then
	repo_args=(--repo "$repo")
fi

if [[ -z "$pr" ]]; then
	pr="$(gh pr view "${repo_args[@]}" --json number --jq .number)"
fi

body="$(gh pr view "$pr" "${repo_args[@]}" --json body --jq .body)"
cleaned="$(
	BODY="$body" python3 - <<'PY'
import os, re
body = os.environ["BODY"]
patterns = [
    r"(?m)^\s*Made with \[Cursor\]\(https://cursor\.com\)\s*$",
    r"(?m)^\s*Made-with:\s*Cursor\s*$",
    r"(?m)^\s*Co-authored-by:\s*Cursor\b.*$",
    r"(?m)^\s*Co-authored-by:\s*Claude\b.*$",
    r"(?m)^\s*Generated with (Claude|Cursor)\b.*$",
    r"(?m)^\s*https://claude\.ai/code/session_[^\s]*\s*$",
]
out = body
for pat in patterns:
    out = re.sub(pat, "", out)
out = re.sub(r"\n{3,}", "\n\n", out).rstrip() + "\n"
print(out, end="")
PY
)"

if [[ "$cleaned" == "$body" ]]; then
	printf 'strip-ai-pr-attribution: no change on PR %s\n' "$pr"
	exit 0
fi

tmp="$(mktemp)"
printf '%s' "$cleaned" >"$tmp"
gh pr edit "$pr" "${repo_args[@]}" --body-file "$tmp"
rm -f "$tmp"
printf 'strip-ai-pr-attribution: cleaned PR %s\n' "$pr"
