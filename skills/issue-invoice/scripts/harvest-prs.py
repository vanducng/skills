#!/usr/bin/env python3
"""Group a client's PRs by local working day, for invoice row drafting.

Usage:
    harvest-prs.py --client <alias> <YYYY-MM>
    harvest-prs.py --list

Client config lives OUTSIDE this repo, at
`~/.config/vd/invoice-rules/<alias>.invoice-rules.md` (YAML frontmatter).

Two things this exists to get right:

  1. `gh pr list` defaults to 30 results and truncates silently. We pass a high
     limit and assert the fetched window reaches back past the target month, so a
     truncated fetch fails loudly instead of returning a plausible short list.
  2. PR timestamps are UTC; the working day is the client's timezone. A PR created
     at 2026-07-02T23:56Z is 7/3 in Asia/Ho_Chi_Minh. Grouping on the raw UTC date
     misfiles work across day and month boundaries.

Run with: ~/.claude/skills/.venv/bin/python3 (needs pyyaml)
"""

import argparse
import collections
import datetime
import json
import pathlib
import subprocess
import sys
import zoneinfo

import yaml

RULES_DIR = pathlib.Path.home() / ".config/vd/invoice-rules"
SUFFIX = ".invoice-rules.md"
LIMIT = 400


def list_clients():
    found = sorted(p.name[: -len(SUFFIX)] for p in RULES_DIR.glob(f"*{SUFFIX}"))
    if not found:
        sys.exit(f"no client rules in {RULES_DIR}\n"
                 f"copy references/client.invoice-rules.example.md to get started")
    for alias in found:
        cfg = load(alias)
        repos = ", ".join(r["slug"] for r in cfg["repos"])
        print(f"{alias:<12} {cfg.get('client', alias):<16} {repos}")


def load(alias):
    path = RULES_DIR / f"{alias}{SUFFIX}"
    if not path.exists():
        avail = sorted(p.name[: -len(SUFFIX)] for p in RULES_DIR.glob(f"*{SUFFIX}"))
        sys.exit(f"no rules for '{alias}' at {path}\n"
                 f"available: {', '.join(avail) if avail else '(none)'}")
    text = path.read_text()
    if not text.startswith("---"):
        sys.exit(f"{path}: missing YAML frontmatter")
    cfg = yaml.safe_load(text.split("---", 2)[1])
    for key in ("timezone", "github_author", "repos"):
        if key not in cfg:
            sys.exit(f"{path}: frontmatter missing required key '{key}'")
    return cfg


def fetch(slug):
    try:
        out = subprocess.run(
            ["gh", "pr", "list", "--repo", slug, "--state", "all", "--limit", str(LIMIT),
             "--json", "number,title,author,createdAt"],
            capture_output=True, text=True, check=True,
        ).stdout
    except subprocess.CalledProcessError as e:
        sys.exit(f"{slug}: gh pr list failed\n{e.stderr.strip()}")
    return json.loads(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("month", nargs="?", help="YYYY-MM")
    ap.add_argument("--client", help="alias under ~/.config/vd/invoice-rules/")
    ap.add_argument("--list", action="store_true", help="list configured clients")
    args = ap.parse_args()

    if args.list:
        return list_clients()
    if not args.client or not args.month:
        ap.error("--client and YYYY-MM are required (or use --list)")

    cfg = load(args.client)
    tz = zoneinfo.ZoneInfo(cfg["timezone"])
    author = cfg["github_author"]
    year, month = (int(x) for x in args.month.split("-"))

    days = collections.defaultdict(list)
    for repo in cfg["repos"]:
        slug, label = repo["slug"], repo.get("label", "")
        prs = fetch(slug)
        stamps = [p["createdAt"] for p in prs]
        if stamps and min(stamps) >= f"{year:04d}-{month:02d}-01":
            sys.exit(
                f"{slug}: fetched {len(prs)} PRs, oldest {min(stamps)[:10]} - the window "
                f"never reaches back to {args.month}, so results would be silently "
                f"incomplete. Raise LIMIT (currently {LIMIT})."
            )
        for p in prs:
            if p["author"]["login"] != author:
                continue
            d = (datetime.datetime.strptime(p["createdAt"], "%Y-%m-%dT%H:%M:%SZ")
                 .replace(tzinfo=datetime.timezone.utc).astimezone(tz))
            if (d.year, d.month) == (year, month):
                cite = f"{label}PR #{p['number']}"
                days[d.date()].append((d.strftime("%H:%M"), cite, p["title"]))

    if not days:
        print(f"no PRs by {author} in {args.month} for {cfg.get('client', args.client)}")
        return

    total = 0
    for day in sorted(days):
        items = sorted(days[day])
        total += len(items)
        bots = sum(1 for _, _, t in items if t.startswith("chore(deps)"))
        note = f"  [{bots} dependency bump - exclude from effort]" if bots else ""
        print(f"\n### {day} {day.strftime('%a')} | {len(items)} PRs "
              f"| {items[0][0]}-{items[-1][0]}{note}")
        for t, cite, title in items:
            print(f"  {t} {cite:<16} {title[:88]}")

    print(f"\n{total} PRs across {len(days)} days in {args.month} "
          f"({cfg.get('client', args.client)}, {cfg['timezone']})")


if __name__ == "__main__":
    main()
