#!/usr/bin/env python3
"""PreToolUse guard — refuse `gh pr merge` while the PR has unresolved review
threads (including the code-review bot's non-blocking inline comments).

This stops an agent (or you) from merging before the review comments are
addressed — the exact failure that let vd-cli #32 merge with 9 open findings.

Contract (Claude Code PreToolUse): reads `{tool_name, tool_input}` JSON on
stdin; exit 2 + stderr blocks the tool; exit 0 allows. Fail-open on any error
(GitHub branch protection is the reliable server-side backstop). Stdlib only.
"""
import json
import re
import subprocess
import sys


def gh(args, cwd=None, timeout=15):
    r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if not re.search(r"\bgh\s+pr\s+merge\b", cmd):
        return 0

    # Resolve gh against the agent's cwd (the repo where the merge would run).
    cwd = (data.get("cwd") or "").strip() or None
    try:
        m = re.search(r"\bgh\s+pr\s+merge\b[^|;&\n]*?\b(\d+)\b", cmd)
        num = int(m.group(1)) if m else int(json.loads(gh(["pr", "view", "--json", "number"], cwd))["number"])
        repo = json.loads(gh(["repo", "view", "--json", "owner,name"], cwd))
        owner, name = repo["owner"]["login"], repo["name"]
        q = ("query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){"
             "pullRequest(number:$n){reviewThreads(first:100){nodes{isResolved isOutdated}}}}}")
        n = gh(["api", "graphql", "-f", "query=" + q, "-f", "o=" + owner, "-f", "r=" + name,
                "-F", "n=" + str(num),
                "--jq", "[.data.repository.pullRequest.reviewThreads.nodes[]"
                        "|select(.isResolved==false and .isOutdated==false)]|length"], cwd)
        unresolved = int(n or 0)
    except Exception:
        return 0  # fail-open

    if unresolved > 0:
        sys.stderr.write(
            f"\nBLOCKED: PR #{num} has {unresolved} unresolved review thread(s).\n"
            f"  Review:  gh pr view {num} --comments\n"
            f"           gh api repos/{owner}/{name}/pulls/{num}/comments --jq '.[].body'\n"
            f"  Then resolve every thread before merging.\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
