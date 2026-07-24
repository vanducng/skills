"""`twitter doctor` - health check for cookies, network, twikit pin."""
from __future__ import annotations

import argparse
import asyncio
import re
import subprocess
import sys
from typing import Callable

from lib import auth
from lib.twikit_client import get_client
from lib.paths import COOKIES_PATH, TOTP_PATH

import twikit


_CT0_RE = re.compile(r"^[0-9a-f]{32,}$")
_AUTH_RE = re.compile(r"^[0-9a-f]{32,}$")


class _Result:
    def __init__(self):
        self.passes = 0
        self.fails = 0
        self.warns = 0

    def pas(self, name: str, msg: str = "") -> None:
        self.passes += 1
        suffix = f" - {msg}" if msg else ""
        print(f"  PASS  {name}{suffix}")

    def fail(self, name: str, msg: str) -> None:
        self.fails += 1
        print(f"  FAIL  {name} - {msg}", file=sys.stderr)

    def warn(self, name: str, msg: str) -> None:
        self.warns += 1
        print(f"  WARN  {name} - {msg}", file=sys.stderr)

    def info(self, name: str, msg: str) -> None:
        print(f"  INFO  {name} - {msg}")


def _check_gopass(r: _Result) -> dict | None:
    try:
        cookies = auth.read_cookies()
    except Exception as exc:
        r.fail("gopass cookies", f"{exc} (run `twitter import-from-dia`)")
        return None
    r.pas("gopass cookies", f"present at {COOKIES_PATH}")
    try:
        auth.read_totp_seed()
        r.pas("gopass totp", f"present at {TOTP_PATH}")
    except Exception as exc:
        r.warn("gopass totp", f"not set ({exc}); `twitter login` will fail")
    return cookies


def _check_cookie_shape(r: _Result, cookies: dict) -> None:
    auth_token = cookies.get("auth_token", "")
    ct0 = cookies.get("ct0", "")
    if not _AUTH_RE.match(auth_token):
        r.fail("cookie shape", f"auth_token doesn't look hex (len={len(auth_token)})")
    else:
        r.pas("cookie shape: auth_token", f"len={len(auth_token)}")
    if not _CT0_RE.match(ct0):
        r.fail("cookie shape", f"ct0 doesn't look hex (len={len(ct0)})")
    else:
        r.pas("cookie shape: ct0", f"len={len(ct0)}")


def _check_twikit_pin(r: _Result) -> None:
    v = getattr(twikit, "__version__", None)
    if v == "2.3.3":
        r.pas("twikit version", v)
    elif v is None:
        r.warn("twikit version", "twikit.__version__ not exposed; cannot verify pin")
    else:
        r.warn("twikit version", f"installed {v}, plan pinned 2.3.3")


async def _check_reachability(r: _Result) -> None:
    try:
        async with get_client() as client:
            await client.get_user_by_screen_name("x")
        r.pas("network reachability", "fetched @x successfully")
    except Exception as exc:
        msg = str(exc)
        low = msg.lower()
        if "401" in msg or "unauthorized" in low:
            r.fail("network reachability", "401 - cookies expired; run `twitter import-from-dia`")
        elif "429" in msg or "rate" in low:
            mins = _parse_rate_limit_minutes(msg)
            extra = f" (~{mins}m until reset)" if mins is not None else ""
            r.warn("network reachability", f"429 rate-limited{extra} (not a config error)")
        elif "226" in msg or "automated" in low:
            r.fail("network reachability", "Error 226 - bot heuristic tripped; use `twitter --use-browser`")
        elif "key_byte" in low or "couldn't get" in low:
            r.fail("network reachability", f"twikit transaction failure: {exc} - check lib/_twikit_patch.py")
        else:
            r.fail("network reachability", msg)


def _parse_rate_limit_minutes(msg: str) -> int | None:
    m = re.search(r"x-rate-limit-reset[:\s]+(\d+)", msg)
    if not m:
        return None
    import time

    reset = int(m.group(1))
    return max(0, (reset - int(time.time())) // 60)


def _check_last_refresh(r: _Result) -> None:
    proc = subprocess.run(
        ["gopass", "git", "log", "-1", "--format=%cr", "--", COOKIES_PATH + ".gpg"],
        capture_output=True,
        text=True,
    )
    out = proc.stdout.strip()
    if proc.returncode == 0 and out:
        r.info("last refresh", f"cookies entry updated {out}")


async def _run(args: argparse.Namespace) -> int:
    r = _Result()
    print("twitter doctor:")
    cookies = _check_gopass(r)
    if cookies is not None:
        _check_cookie_shape(r, cookies)
    _check_twikit_pin(r)
    if cookies is not None and not args.offline:
        await _check_reachability(r)
    _check_last_refresh(r)
    print(f"  ---  {r.passes} pass · {r.fails} fail · {r.warns} warn")
    return 1 if r.fails else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="twitter doctor")
    p.add_argument("--offline", action="store_true", help="skip the network check")
    args = p.parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
