"""Error classifier + auto-fallback dispatcher for twikit -> agent-browser.

When twikit raises an internal-API-drift exception (transaction-init failure,
KeyError on a renamed legacy field) or X returns Error 226 ("looks
automated"), call_with_fallback transparently swaps to the browser path.
TWITTER_USE_BROWSER=1 forces the swap from the start.
"""
from __future__ import annotations

import os
import sys
from typing import Awaitable, Callable

BREAKAGE_EXCEPTIONS: tuple[type[Exception], ...] = (KeyError, IndexError, AttributeError)
BREAKAGE_SUBSTRINGS: tuple[str, ...] = (
    "key_byte indices",
    "couldn't get",
    "ondemand.s",
    "itemcontent",
)
ERROR_226_SUBSTRINGS: tuple[str, ...] = ("226", "looks automated", "looks like it might be automated")


def is_226(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(t in msg for t in ERROR_226_SUBSTRINGS)


def is_transaction_drift(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(t in msg for t in BREAKAGE_SUBSTRINGS)


def use_browser_env() -> bool:
    return os.environ.get("TWITTER_USE_BROWSER", "0") == "1"


def _from_twikit(exc: BaseException) -> bool:
    """True if any frame in the traceback originates inside the twikit package.

    Without this, classifying every `KeyError`/`IndexError`/`AttributeError`
    as drift would also swallow bugs in our own cmd_*.py code.
    """
    tb = exc.__traceback__
    while tb is not None:
        filename = tb.tb_frame.f_code.co_filename
        if "/twikit/" in filename or "\\twikit\\" in filename:
            return True
        tb = tb.tb_next
    return False


def should_fallback(exc: BaseException) -> bool:
    if is_226(exc) or is_transaction_drift(exc):
        return True
    return isinstance(exc, BREAKAGE_EXCEPTIONS) and _from_twikit(exc)


async def call_with_fallback(
    twikit_fn: Callable[..., Awaitable],
    browser_fn: Callable[..., Awaitable],
    *args,
    **kwargs,
):
    """Call `twikit_fn(*args, **kwargs)`; on classified breakage call `browser_fn`."""
    if use_browser_env():
        return await browser_fn(*args, **kwargs)
    try:
        return await twikit_fn(*args, **kwargs)
    except BaseException as exc:
        if should_fallback(exc):
            print(
                f"twitter: twikit hit {type(exc).__name__}: {exc} - falling back to browser",
                file=sys.stderr,
            )
            return await browser_fn(*args, **kwargs)
        raise


__all__ = [
    "is_226",
    "is_transaction_drift",
    "should_fallback",
    "use_browser_env",
    "call_with_fallback",
    "BREAKAGE_EXCEPTIONS",
    "BREAKAGE_SUBSTRINGS",
]
