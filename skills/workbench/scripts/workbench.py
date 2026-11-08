#!/usr/bin/env python3
"""Compatibility shim. The workbench is now records.cjs (see SKILL.md).

`new [slug]` still works for the producer skills that call it: it runs `records.cjs init`; `--ticket` and `--parent` are refused. Every other old
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
        flags = [a for a in rest if a.startswith("--")]
        if flags:
            words = [a for a in rest if not a.startswith("--")]
            ticket = next((a.split("=", 1)[1] for a in rest if a.startswith("--ticket=")), None)
            if ticket is None and "--ticket" in rest and rest.index("--ticket") + 1 < len(rest):
                ticket = rest[rest.index("--ticket") + 1]
            slug = next((w for w in words if w != ticket), "slug")
            sys.stderr.write(
                f"workbench.py new: {flags[0].split('=')[0]} was removed; the id is the slug alone, so put a ticket in it: "
                f"workbench.py new {ticket + '-' if ticket else ''}{slug}\n"
            )
            return 2
        slug = rest[0] if rest else None
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
