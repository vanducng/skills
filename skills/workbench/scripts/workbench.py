#!/usr/bin/env python3
"""Compatibility shim. The workbench is now records.cjs (see SKILL.md).

`new [slug]` still works for the producer skills that call it: it runs `records.cjs init`. Every other old
command prints "removed" and exits 2. Remove this file when no skill calls `workbench new` any more.
"""
import os
import re
import subprocess
import sys

RECORDS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "records.cjs")
REMOVED = {"resolve", "switch", "list", "status", "archive", "restore", "reindex", "gc", "migrate", "triage"}


def main(argv):
    cmd = argv[0] if argv else ""
    if cmd == "new":
        rest = argv[1:]
        slug = None
        i = 0
        while i < len(rest):
            if rest[i] in ("--ticket", "--parent"):
                i += 2
                continue
            if rest[i].startswith("--"):
                i += 1
                continue
            slug = slug or rest[i]
            i += 1
        args = ["node", RECORDS, "init"]
        if slug:
            args += ["--id", re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")]
        sys.stderr.write("workbench.py new: now runs records.cjs init (record folder .workbench/<id>/)\n")
        return subprocess.call(args)
    if cmd in REMOVED:
        sys.stderr.write(
            f"workbench.py {cmd}: removed. Use `node {RECORDS} resolve|init|check|proof add|migrate` (see the workbench skill).\n"
        )
        return 2
    sys.stderr.write("usage: workbench.py new [slug]   (other commands were removed; see the workbench skill)\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
