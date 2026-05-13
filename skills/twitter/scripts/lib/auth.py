"""Cookie / credential storage via gopass + ephemeral tempfile handoff to twikit.

All secrets stay in gopass. The cookie tempfile is mode 0o600 and unlinked on
context exit (atexit-registered as a belt-and-suspenders).
"""
from __future__ import annotations

import atexit
import json
import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .paths import COOKIES_PATH, CREDS_PATH, TOTP_PATH


class CookiesMissing(RuntimeError):
    """Raised when no cookie entry is in gopass yet."""


class CredentialsMissing(RuntimeError):
    """Raised when login credentials are not in gopass."""


def _gopass_show(path: str, missing_exc: type = CookiesMissing) -> str:
    """Run `gopass show -o <path>`. Non-zero exit → raise `missing_exc`."""
    proc = subprocess.run(
        ["gopass", "show", "-o", path],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise missing_exc(
            f"gopass entry not found: {path} (stderr: {proc.stderr.strip()})"
        )
    return proc.stdout.strip()


def read_cookies() -> dict:
    """Return the current cookie dict from gopass."""
    raw = _gopass_show(COOKIES_PATH, CookiesMissing)
    if not raw:
        raise CookiesMissing(f"empty gopass entry: {COOKIES_PATH}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CookiesMissing(
            f"gopass entry {COOKIES_PATH} is not valid JSON: {exc}"
        ) from exc


def write_cookies(d: dict) -> None:
    """Persist the cookie dict to gopass (overwrites)."""
    payload = json.dumps(d).encode()
    proc = subprocess.run(
        ["gopass", "insert", "-f", COOKIES_PATH],
        input=payload,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"gopass insert failed for {COOKIES_PATH}: {proc.stderr.decode().strip()}"
        )


@contextmanager
def cookie_tempfile(d: dict):
    """Yield a 0o600 tempfile path containing the cookie JSON; unlink on exit."""
    fd, path = tempfile.mkstemp(prefix="twitter-cookies-", suffix=".json")
    os.fchmod(fd, 0o600)
    cleanup_done = {"v": False}

    def _cleanup():
        if cleanup_done["v"]:
            return
        cleanup_done["v"] = True
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass

    atexit.register(_cleanup)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(d, f)
        yield path
    finally:
        _cleanup()


def read_totp_seed() -> str:
    """Return the raw base32 TOTP seed (for twikit's totp_secret arg)."""
    raw = _gopass_show(TOTP_PATH, CredentialsMissing)
    if not raw:
        raise CredentialsMissing(f"empty gopass entry: {TOTP_PATH}")
    return raw


def read_totp_code() -> str:
    """Return the live 6-digit TOTP code (uses gopass otp)."""
    proc = subprocess.run(
        ["gopass", "otp", "-o", TOTP_PATH],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise CredentialsMissing(
            f"gopass otp failed for {TOTP_PATH}: {proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def read_credentials() -> dict:
    """Parse the multi-line gopass credentials entry.

    Layout:
        line 1     : password
        username:  : screen-name / login handle
        email:     : email address
    """
    raw = _gopass_show(CREDS_PATH, CredentialsMissing)
    if not raw:
        raise CredentialsMissing(f"empty gopass entry: {CREDS_PATH}")
    lines = raw.splitlines()
    out = {"password": lines[0].strip() if lines else ""}
    for line in lines[1:]:
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip().lower()] = v.strip()
    return out


__all__ = [
    "CookiesMissing",
    "CredentialsMissing",
    "read_cookies",
    "write_cookies",
    "cookie_tempfile",
    "read_totp_seed",
    "read_totp_code",
    "read_credentials",
]
