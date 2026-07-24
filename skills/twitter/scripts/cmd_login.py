"""`twitter login` - fallback bootstrap via twikit's login flow (gopass-backed).

Use when `import-from-dia` isn't available (Dia not installed, non-mac, or
session expired without a Dia bootstrap path). Reads username/password/TOTP
seed from gopass; writes the resulting cookies back.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

from lib import auth
from lib._twikit_patch import apply as _apply_patch

_apply_patch()
import twikit  # noqa: E402


async def _run(args: argparse.Namespace) -> int:
    creds = auth.read_credentials()
    username = args.auth_info_1 or creds.get("username")
    email = creds.get("email")
    password = creds.get("password")
    if not username or not password:
        print("twitter login: missing username/password in gopass credentials entry", file=sys.stderr)
        return 2
    totp_seed = auth.read_totp_seed()

    client = twikit.Client(language="en-US")
    try:
        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password,
            totp_secret=totp_seed,
            enable_ui_metrics=True,
        )
    except Exception as exc:
        msg = str(exc)
        if "DenyLoginSubtask" in msg or "verification" in msg.lower():
            print(
                "twitter login: X requires manual verification - open x.com in Dia "
                "and complete the challenge, then run `twitter import-from-dia`.",
                file=sys.stderr,
            )
            return 1
        print(f"twitter login: {exc}", file=sys.stderr)
        return 1

    fd, tmp = tempfile.mkstemp(prefix="twitter-login-", suffix=".json")
    os.close(fd)
    Path(tmp).chmod(0o600)
    try:
        client.save_cookies(tmp)
        with open(tmp) as f:
            cookies = json.load(f)
        auth.write_cookies(cookies)
    finally:
        try:
            Path(tmp).unlink()
        except FileNotFoundError:
            pass
    print("login ok - cookies saved to gopass")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="twitter login")
    p.add_argument("--auth-info-1", help="override username (default: gopass credentials line `username:`)")
    args = p.parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
