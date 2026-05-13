"""Async twikit Client factory with cookie tempfile handoff + write-back.

Reads cookies from gopass, materializes them to a 0o600 tempfile for the
duration of the call, and on exit persists any refreshed cookies back to
gopass (only if changed — twikit doesn't always rotate ct0 on read ops).

The community patch for twikit's broken `ClientTransaction.init()` is applied
at module import time, before any twikit Client is constructed.
"""
from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager

from . import _twikit_patch

_twikit_patch.apply()

import twikit  # noqa: E402

from . import auth  # noqa: E402


@asynccontextmanager
async def get_client(language: str = "en-US"):
    """Yield a logged-in twikit Client; persist refreshed cookies on exit."""
    cookies_before = auth.read_cookies()
    with auth.cookie_tempfile(cookies_before) as path:
        client = twikit.Client(language=language)
        client.load_cookies(path)
        try:
            yield client
        finally:
            try:
                client.save_cookies(path)
                with open(path) as f:
                    cookies_after = json.load(f)
                if cookies_after != cookies_before:
                    auth.write_cookies(cookies_after)
            except Exception as exc:
                print(
                    f"twitter: cookie write-back failed: {exc} "
                    "(rerun `twitter import-from-dia` if reads start 401-ing)",
                    file=sys.stderr,
                )


__all__ = ["get_client"]
