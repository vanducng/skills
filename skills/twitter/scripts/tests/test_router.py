"""Unit tests for the router classifier + call_with_fallback."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from lib import router


def _run(coro):
    return asyncio.run(coro)


def test_is_226_matches_x_error_text():
    msg = (
        "Authorization: This request looks like it might be automated. "
        "Please try again later. (226)"
    )
    assert router.is_226(Exception(msg))


def test_is_226_matches_short_form():
    assert router.is_226(Exception("Error 226"))


def test_is_transaction_drift_catches_key_byte_error():
    assert router.is_transaction_drift(Exception("Couldn't get KEY_BYTE indices"))


def test_is_transaction_drift_catches_ondemand_marker():
    assert router.is_transaction_drift(Exception("ondemand.s not found"))


def _make_twikit_exc(exc: Exception) -> Exception:
    """Synthesize a traceback that passes through a fake twikit/ frame."""
    import types

    fake_code = compile("raise exc", "/site-packages/twikit/fake.py", "exec")
    try:
        exec(fake_code, {"exc": exc})
    except Exception as caught:
        return caught
    raise AssertionError("synthesizer didn't raise")


def test_should_fallback_for_keyerror_from_twikit():
    assert router.should_fallback(_make_twikit_exc(KeyError("urls")))


def test_should_fallback_false_for_keyerror_from_user_code():
    # bare KeyError raised here has no twikit frame in traceback
    try:
        raise KeyError("oops")
    except KeyError as exc:
        assert not router.should_fallback(exc)


def test_should_fallback_false_for_valueerror():
    assert not router.should_fallback(ValueError("plain"))


def test_call_with_fallback_uses_twikit_when_no_error():
    async def tw(x): return f"tw:{x}"
    async def br(x): return f"br:{x}"
    assert _run(router.call_with_fallback(tw, br, 1)) == "tw:1"


def test_call_with_fallback_swaps_on_keyerror_from_twikit():
    async def tw(x):
        raise _make_twikit_exc(KeyError("urls"))
    async def br(x): return f"br:{x}"
    assert _run(router.call_with_fallback(tw, br, 1)) == "br:1"


def test_call_with_fallback_swaps_on_226():
    async def tw(x): raise Exception("Error 226 looks automated")
    async def br(x): return "browser"
    assert _run(router.call_with_fallback(tw, br, 1)) == "browser"


def test_call_with_fallback_reraises_on_unrelated():
    async def tw(x): raise ValueError("bad input")
    async def br(x): return "browser"
    with pytest.raises(ValueError):
        _run(router.call_with_fallback(tw, br, 1))


def test_call_with_fallback_honors_use_browser_env(monkeypatch):
    monkeypatch.setenv("TWITTER_USE_BROWSER", "1")
    twikit_called = []
    async def tw(x):
        twikit_called.append(x)
        return "tw"
    async def br(x):
        return "br"
    assert _run(router.call_with_fallback(tw, br, 1)) == "br"
    assert twikit_called == []
