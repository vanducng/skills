"""`twitter import-from-dia` - bootstrap cookies from the local Dia browser."""
from __future__ import annotations

import argparse
import sys

from lib import auth
from lib.dia_cookies import (
    DEFAULT_PROFILE,
    BootstrapError,
    KeychainError,
    UnsupportedCookieFormat,
    extract,
)


def _redact(s: str) -> str:
    if len(s) <= 8:
        return "***"
    return s[:4] + "…" + s[-4:]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="twitter import-from-dia",
        description="Decrypt x.com cookies from the local Dia browser and store in gopass.",
    )
    p.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
        help=f"Dia profile name (default: {DEFAULT_PROFILE!r})",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print redacted keys, do not write to gopass.",
    )
    args = p.parse_args(argv)

    try:
        cookies = extract(args.profile)
    except KeychainError as e:
        print(f"twitter: keychain error - {e}", file=sys.stderr)
        return 3
    except FileNotFoundError as e:
        print(f"twitter: profile path missing - {e}", file=sys.stderr)
        return 4
    except UnsupportedCookieFormat as e:
        print(f"twitter: unsupported cookie format - {e}", file=sys.stderr)
        return 5
    except BootstrapError as e:
        print(f"twitter: {e}", file=sys.stderr)
        return 6

    if args.dry_run:
        for k in ("auth_token", "ct0"):
            v = cookies.get(k, "")
            print(f"  {k}: {_redact(v)} (len={len(v)})")
        print("dry-run: not written to gopass")
        return 0

    auth.write_cookies(cookies)
    print(
        "imported auth_token (rotates ~quarterly), ct0 (rotates per action) "
        "→ personal/x-twitter/cookies"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
