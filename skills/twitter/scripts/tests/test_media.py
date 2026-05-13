"""Unit tests for lib.media.upload — validation only (no network)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from lib import media as media_lib


class _StubClient:
    def __init__(self):
        self.calls: list[tuple] = []

    async def upload_media(self, path, **kwargs):
        self.calls.append((path, kwargs))
        return f"id-{Path(path).name}"


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if sys.version_info < (3, 10) else asyncio.run(coro)


def test_upload_rejects_missing_file():
    with pytest.raises(FileNotFoundError):
        _run(media_lib.upload(_StubClient(), ["/nonexistent/file.jpg"]))


def test_upload_rejects_oversize_image(tmp_path):
    p = tmp_path / "big.jpg"
    p.write_bytes(b"x" * (6 * 1024 * 1024))
    with pytest.raises(media_lib.MediaTooLarge):
        _run(media_lib.upload(_StubClient(), [str(p)]))


def test_upload_rejects_unknown_mime(tmp_path):
    p = tmp_path / "weird.xyz"
    p.write_bytes(b"x")
    with pytest.raises(media_lib.MediaUnsupported):
        _run(media_lib.upload(_StubClient(), [str(p)]))


def test_upload_returns_ids_in_order(tmp_path):
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.jpg"
    a.write_bytes(b"x" * 10)
    b.write_bytes(b"x" * 10)
    client = _StubClient()
    ids = _run(media_lib.upload(client, [str(a), str(b)]))
    assert ids == ["id-a.jpg", "id-b.jpg"]


def test_upload_video_passes_category(tmp_path):
    p = tmp_path / "clip.mp4"
    p.write_bytes(b"x" * 10)
    client = _StubClient()
    _run(media_lib.upload(client, [str(p)]))
    _, kwargs = client.calls[0]
    assert kwargs.get("media_category") == "tweet_video"
    assert kwargs.get("wait_for_completion") is True
