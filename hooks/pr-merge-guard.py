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
import os
import re
import subprocess
import sys


def gh(args, cwd=None, timeout=15):
    r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def tool_name(data):
    name = data.get("tool_name") or data.get("toolName") or ""
    aliases = {
        "run_terminal_command": "Bash",
        "bash": "Bash",
        "Bash": "Bash",
    }
    return aliases.get(name, aliases.get(str(name).lower(), name))


def tool_input(data):
    value = data.get("tool_input")
    if isinstance(value, dict):
        return value
    value = data.get("toolInput")
    return value if isinstance(value, dict) else {}


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(data, dict):
        return 0
    if tool_name(data) != "Bash":
        return 0
    cmd = tool_input(data).get("command", "") or ""
    if not re.search(r"\bgh\s+pr\s+merge\b", cmd):
        return 0

    # Resolve the repo the merge actually targets, not merely the session cwd:
    # an explicit -R/--repo wins, else a leading `cd <dir> &&`, else the agent's cwd.
    # Without this a cross-repo merge is checked against the wrong PR number.
    cwd = (data.get("cwd") or "").strip() or None
    m = re.search(r"(?:-R|--repo)[=\s]+([^\s|;&]+/[^\s|;&]+)", cmd)
    repo_flag = m.group(1) if m else None
    if not repo_flag:
        m = re.search(r"^\s*cd\s+([^\s|;&]+)\s*&&", cmd)
        if m:
            cwd = os.path.expanduser(m.group(1).strip("'\""))

    try:
        m = re.search(r"\bgh\s+pr\s+merge\b[^|;&\n]*?\b(\d+)\b", cmd)
        num = int(m.group(1)) if m else int(json.loads(gh(["pr", "view", "--json", "number"], cwd))["number"])
        if repo_flag:
            owner, name = repo_flag.split("/", 1)
        else:
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
