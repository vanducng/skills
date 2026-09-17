#!/usr/bin/env python3
"""Audit common macOS global hotkey owners without printing unrelated preferences."""

from __future__ import annotations

import argparse
import json
import plistlib
import re
import sys
from pathlib import Path
from typing import Any

KEY_NAMES = {
    0: "a", 1: "s", 2: "d", 3: "f", 4: "h", 5: "g", 6: "z", 7: "x",
    8: "c", 9: "v", 11: "b", 12: "q", 13: "w", 14: "e", 15: "r",
    16: "y", 17: "t", 18: "1", 19: "2", 20: "3", 21: "4", 22: "6",
    23: "5", 25: "9", 26: "7", 28: "8", 29: "0", 31: "o", 32: "u",
    34: "i", 35: "p", 37: "l", 38: "j", 40: "k", 45: "n", 46: "m",
    49: "space", 51: "delete", 115: "home", 119: "end", 123: "left",
    124: "right", 125: "down", 126: "up",
}
MODIFIER_BITS = ((256, "cmd"), (512, "shift"), (2048, "opt"), (4096, "ctrl"))
SKHD_MODIFIERS = {
    "cmd": {"cmd"}, "command": {"cmd"}, "ctrl": {"ctrl"},
    "control": {"ctrl"}, "alt": {"opt"}, "option": {"opt"},
    "opt": {"opt"}, "shift": {"shift"},
    "meh": {"ctrl", "opt", "shift"},
    "hyper": {"ctrl", "opt", "shift", "cmd"},
}


def plist_path(domain: str) -> Path:
    return Path.home() / "Library" / "Preferences" / f"{domain}.plist"


def load_plist(domain: str) -> dict[str, Any]:
    path = plist_path(domain)
    if not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            value = plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException):
        return {}
    return value if isinstance(value, dict) else {}


def decode_json(value: Any) -> dict[str, Any] | None:
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def key_name(code: Any) -> str:
    return KEY_NAMES.get(code, f"keycode-{code}")


def chord(modifiers: set[str], code: Any) -> tuple[frozenset[str], str]:
    return frozenset(modifiers), key_name(code)


def display_chord(value: tuple[frozenset[str], str]) -> str:
    modifiers, key = value
    ordered = [name for _, name in MODIFIER_BITS if name in modifiers]
    return "+".join([*ordered, key])


def from_carbon(data: dict[str, Any]) -> tuple[frozenset[str], str] | None:
    code = data.get("carbonKeyCode", data.get("carbonKey"))
    if not isinstance(code, int):
        return None
    modifiers = {name for bit, name in MODIFIER_BITS if data.get("carbonModifiers", 0) & bit}
    return chord(modifiers, code)


def add_record(records: list[dict[str, Any]], owner: str, action: str,
               value: tuple[frozenset[str], str], scope: str = "systemGlobal") -> None:
    records.append({
        "owner": owner,
        "action": action,
        "scope": scope,
        "chord": display_chord(value),
        "_identity": [sorted(value[0]), value[1]],
    })


def parse_alter(records: list[dict[str, Any]]) -> None:
    for key, raw in load_plist("com.wearedevx.alter").items():
        if not key.startswith("KeyboardShortcuts_"):
            continue
        data = decode_json(raw)
        if not data:
            continue
        scope = data.get("access", "unknown")
        value = from_carbon(data)
        if value and scope == "systemGlobal":
            add_record(records, "Alter", key, value, scope)


def parse_tinycast(records: list[dict[str, Any]]) -> None:
    for key, raw in load_plist("com.tinycast.app").items():
        if not key.startswith("hotkey."):
            continue
        data = decode_json(raw)
        if not data:
            continue
        combo_data = data.get("combo", {}).get("_0", {})
        value = from_carbon(combo_data) if isinstance(combo_data, dict) else None
        if value:
            add_record(records, "Tinycast", key, value)


def parse_cleanshot(records: list[dict[str, Any]]) -> None:
    for key, raw in load_plist("pl.maketheweb.cleanshotx").items():
        if not key.startswith("LAVA"):
            continue
        data = decode_json(raw)
        value = from_carbon(data or {})
        if value:
            add_record(records, "CleanShot", key, value)


def parse_skhd(records: list[dict[str, Any]]) -> None:
    path = Path.home() / ".config" / "skhd" / "skhdrc"
    if not path.exists():
        return
    pattern = re.compile(r"^\s*([^:#]+?)\s+-\s+([^\s:]+)\s*:")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line_number, line in enumerate(lines, 1):
        match = pattern.match(line)
        if not match:
            continue
        raw_modifiers, raw_key = match.groups()
        modifiers: set[str] = set()
        known = True
        for token in (part.strip().lower() for part in raw_modifiers.split("+")):
            token_modifiers = SKHD_MODIFIERS.get(token)
            if token_modifiers is None:
                known = False
                break
            modifiers.update(token_modifiers)
        if not known:
            continue
        key = raw_key.lower()
        if key.startswith("0x"):
            try:
                key = key_name(int(key, 16))
            except ValueError:
                pass
        value = (frozenset(modifiers), key)
        add_record(records, "skhd", f"{path}:line {line_number}", value)


def audit() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    parse_alter(records)
    parse_tinycast(records)
    parse_cleanshot(records)
    parse_skhd(records)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--strict", action="store_true", help="exit 1 when a chord collides")
    parser.add_argument("--self-test", action="store_true", help="run built-in checks")
    args = parser.parse_args()

    if args.self_test:
        assert key_name(15) == "r"
        assert display_chord(chord({"cmd", "shift"}, 15)) == "cmd+shift+r"
        assert from_carbon({"carbonKeyCode": 2, "carbonModifiers": 768}) == (
            frozenset({"cmd", "shift"}), "d"
        )
        print("self-test: ok")
        return 0

    records = audit()
    groups: dict[tuple[tuple[str, ...], str], list[dict[str, Any]]] = {}
    for record in records:
        identity = (tuple(record.pop("_identity")[0]), record["chord"].split("+")[-1])
        groups.setdefault(identity, []).append(record)
    collisions = [items for items in groups.values() if len(items) > 1]

    if args.json:
        print(json.dumps({"bindings": records, "collisions": collisions}, indent=2))
    else:
        for record in sorted(records, key=lambda item: (item["chord"], item["owner"], item["action"])):
            print(f"{record['chord']:<24} {record['owner']:<10} {record['action']}")
        print()
        if collisions:
            print("collisions:")
            for items in collisions:
                print(f"  {items[0]['chord']}: " + ", ".join(item["owner"] for item in items))
        else:
            print("collisions: none")

    return 1 if args.strict and collisions else 0


if __name__ == "__main__":
    raise SystemExit(main())
