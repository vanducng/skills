"""Unit tests for cmd_post text validator."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cmd_post import _validate_text


def test_short_text_no_long_ok():
    assert _validate_text("hello", long_flag=False) is None


def test_long_text_without_long_flag_errors():
    err = _validate_text("x" * 281, long_flag=False)
    assert err is not None
    assert "281" in err
    assert "--long" in err


def test_long_text_with_long_flag_ok():
    assert _validate_text("x" * 500, long_flag=True) is None


def test_exactly_280_chars_no_long_flag_ok():
    assert _validate_text("x" * 280, long_flag=False) is None
