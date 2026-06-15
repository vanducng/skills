#!/usr/bin/env python3
"""Wire agent-notify.py into Claude Code + Codex. Idempotent; backs up configs.

Run on any machine after exporting TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID (see README).
"""
import json
import os
import re
import shutil
import stat
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "agent-notify.py")
HOME = os.path.expanduser("~")


def backup(path):
    b = f"{path}.bak.{datetime.now():%Y%m%d%H%M%S}"
    shutil.copy2(path, b)
    return b


def ensure_exec(path):
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def wire_claude():
    path = os.path.join(HOME, ".claude", "settings.json")
    data = json.load(open(path)) if os.path.exists(path) else {}
    hooks = data.setdefault("hooks", {})
    changed = False
    for event, arg in (("Stop", "stop"), ("Notification", "notification")):
        cmd = f'python3 "$HOME/skills/hooks/agent-notify.py" claude {arg}'
        arr = hooks.setdefault(event, [])
        present = any("agent-notify.py" in h.get("command", "") and f"claude {arg}" in h.get("command", "")
                      for blk in arr for h in blk.get("hooks", []))
        if not present:
            arr.append({"hooks": [{"type": "command", "command": cmd}]})
            changed = True
    if changed:
        if os.path.exists(path):
            backup(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
    return "wired" if changed else "already wired"


def wire_codex():
    path = os.path.join(HOME, ".codex", "config.toml")
    if not os.path.exists(path):
        return "no ~/.codex/config.toml (skipped)"
    txt = open(path).read()
    new = f'notify = ["python3", "{SCRIPT}", "codex"]'
    m = re.search(r"(?m)^\s*notify\s*=.*$", txt)
    if m and m.group(0).strip() == new:
        return "already wired"
    note = ""
    if m:
        prev = m.group(0).strip()
        if "agent-notify.py" not in prev:
            note = f" (previous notify preserved — set CODEX_NOTIFY_FORWARD in ~/.envrc to chain it: {prev})"
        txt = txt[:m.start()] + new + txt[m.end():]
    else:
        txt = txt.rstrip() + "\n" + new + "\n"
    backup(path)
    open(path, "w").write(txt)
    return "wired" + note


if __name__ == "__main__":
    ensure_exec(SCRIPT)
    print("script :", SCRIPT)
    print("claude :", wire_claude())
    print("codex  :", wire_codex())
    print("\nReminder: export TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (e.g. in ~/.envrc).")
