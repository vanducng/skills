"""Unit tests for cmd_doctor - cookie shape + rate-limit parsing."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cmd_doctor import _Result, _check_cookie_shape, _parse_rate_limit_minutes


def test_cookie_shape_passes_for_valid_hex():
    r = _Result()
    _check_cookie_shape(r, {"auth_token": "a" * 40, "ct0": "b" * 160})
    assert r.fails == 0
    assert r.passes == 2


def test_cookie_shape_fails_for_short_auth():
    r = _Result()
    _check_cookie_shape(r, {"auth_token": "abc", "ct0": "b" * 160})
    assert r.fails == 1


def test_cookie_shape_fails_for_missing_ct0():
    r = _Result()
    _check_cookie_shape(r, {"auth_token": "a" * 40, "ct0": ""})
    assert r.fails == 1


def test_parse_rate_limit_minutes_returns_none_when_absent():
    assert _parse_rate_limit_minutes("plain error message") is None


def test_parse_rate_limit_minutes_extracts_epoch_and_returns_minutes():
    import time

    future = int(time.time()) + 600
    msg = f"429 too many requests x-rate-limit-reset: {future}"
    mins = _parse_rate_limit_minutes(msg)
    assert mins is not None
    assert 8 <= mins <= 11
