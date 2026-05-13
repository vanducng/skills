"""Unit tests for url_parser.parse_target."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from lib.url_parser import Target, parse_target


def test_parse_x_status_url():
    assert parse_target("https://x.com/jack/status/12345") == Target("tweet", "12345")


def test_parse_twitter_status_url():
    assert parse_target("https://twitter.com/jack/status/12345") == Target("tweet", "12345")


def test_parse_x_status_url_with_www():
    assert parse_target("https://www.x.com/jack/status/99") == Target("tweet", "99")


def test_parse_numeric_id():
    assert parse_target("2052894872563028474") == Target("tweet", "2052894872563028474")


def test_parse_handle_with_at():
    assert parse_target("@jack") == Target("user", "jack")


def test_parse_handle_without_at():
    assert parse_target("jack") == Target("user", "jack")


def test_parse_search():
    assert parse_target("search:claude code") == Target("search", "claude code")


def test_parse_search_case_insensitive():
    assert parse_target("Search:foo") == Target("search", "foo")


def test_empty_raises():
    with pytest.raises(ValueError):
        parse_target("   ")


def test_search_without_query_raises():
    with pytest.raises(ValueError):
        parse_target("search:")


def test_handle_too_long_falls_through_to_error():
    with pytest.raises(ValueError):
        parse_target("a_handle_way_longer_than_fifteen_chars")
