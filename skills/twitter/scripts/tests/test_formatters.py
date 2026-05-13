"""Unit tests for tweet_to_dict / tweet_to_md."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.formatters import tweet_to_dict, tweet_to_md, tweets_to_md


def _fixture_tweet():
    user = SimpleNamespace(id="42", screen_name="jack", name="jack dorsey")
    media = [SimpleNamespace(type="photo", media_url_https="https://pbs.twimg.com/x.jpg")]
    return SimpleNamespace(
        id="2049336710572728783",
        created_at="Wed Apr 29 03:55:21 +0000 2026",
        user=user,
        text="hello world",
        reply_count=1,
        retweet_count=2,
        favorite_count=3,
        view_count=4,
        urls=[{"expanded_url": "https://example.com"}],
        media=media,
        is_quote_status=False,
        conversation_id="2049336710572728783",
    )


def test_tweet_to_dict_shape():
    d = tweet_to_dict(_fixture_tweet())
    assert d["id"] == "2049336710572728783"
    assert d["text"] == "hello world"
    assert d["author"] == {"id": "42", "screen_name": "jack", "name": "jack dorsey"}
    assert d["media"] == [{"type": "photo", "url": "https://pbs.twimg.com/x.jpg"}]
    assert d["urls"] == ["https://example.com"]
    assert d["favorite_count"] == 3


def test_tweet_to_md_contains_handle_text_and_url():
    md = tweet_to_md(_fixture_tweet())
    assert "@jack" in md
    assert "hello world" in md
    assert "https://x.com/jack/status/2049336710572728783" in md
    assert "♥ 3" in md


def test_tweets_to_md_separates_with_hr():
    md = tweets_to_md([_fixture_tweet(), _fixture_tweet()])
    assert "\n\n---\n\n" in md


def test_tweets_to_md_empty_returns_placeholder():
    assert tweets_to_md([]) == "_(no tweets)_"


def test_tweet_to_dict_handles_missing_user():
    t = SimpleNamespace(
        id="1", created_at="x", user=None, text="t",
        reply_count=0, retweet_count=0, favorite_count=0, view_count=0,
        urls=None, media=None, is_quote_status=False, conversation_id="1",
    )
    d = tweet_to_dict(t)
    assert d["author"] is None
    assert d["urls"] == []
    assert d["media"] == []
