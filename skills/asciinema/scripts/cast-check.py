#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyte"]
# ///
"""Replay an asciinema cast through a terminal emulator: report when each expected screen appears, dump screens at times."""
import argparse
import json
import sys

import pyte


def events(lines, header):
    v3 = header.get("version", 2) >= 3
    limit = header.get("idle_time_limit")
    clock = prev = 0.0
    for raw in lines[1:]:
        if not raw.strip() or raw.startswith("#"):
            continue
        t, kind, data = json.loads(raw)
        delta = t if v3 else t - prev
        prev = t
        clock += min(delta, limit) if limit else delta
        yield clock, kind, data


def show(screen, at, rows):
    print(f"=== t={at}")
    body = [line.rstrip() for line in screen.display[:rows]]
    while body and not body[-1]:
        body.pop()
    print("\n".join(body))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cast")
    p.add_argument("--expect", action="append", default=[], metavar="LABEL=TEXT", help="text that must appear on screen")
    p.add_argument("--at", action="append", default=[], type=float, metavar="SECONDS", help="print the screen at this time")
    p.add_argument("--rows", type=int, default=999, help="rows to print per --at dump")
    a = p.parse_args()

    markers = {}
    for item in a.expect:
        label, sep, needle = item.partition("=")
        if not sep or not needle:
            p.error(f"--expect needs LABEL=TEXT, got {item!r}")
        markers[label] = needle

    lines = open(a.cast, encoding="utf-8").read().splitlines()
    header = json.loads(lines[0])
    term = header.get("term", {})
    screen = pyte.Screen(term.get("cols") or header["width"], term.get("rows") or header["height"])
    stream = pyte.Stream(screen)
    seen, wants, clock, exit_code = {}, sorted(a.at), 0.0, None
    for clock, kind, data in events(lines, header):
        while wants and clock > wants[0]:
            show(screen, wants.pop(0), a.rows)
        if kind == "o":
            stream.feed(data)
            if len(seen) < len(markers):
                text = "\n".join(screen.display)
                for label, needle in markers.items():
                    if label not in seen and needle in text:
                        seen[label] = round(clock, 1)
        elif kind == "r":
            cols, rows = (int(n) for n in data.split("x"))
            screen.resize(rows, cols)
        elif kind == "x":
            exit_code = int(data)
    for at in wants:
        show(screen, at, a.rows)

    width = max((len(label) for label in markers), default=0)
    for label in markers:
        print(f"{label:{width}}  {seen.get(label, 'MISSING')}")
    print(f"duration {clock:.1f}s, exit {exit_code if exit_code is not None else 'not recorded'}")
    missing = len(markers) - len(seen)
    if missing or exit_code not in (None, 0):
        sys.exit(f"{missing} expected screen(s) missing" if missing else f"session exited {exit_code}")
    if markers:
        print("all present")


if __name__ == "__main__":
    main()
