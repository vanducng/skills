"""Tests for the unified --provider switch and Codex-first auto cascade."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gemini_batch_process as gbp  # noqa: E402
import codex_imagegen as cig  # noqa: E402


@pytest.fixture
def base_kwargs(tmp_path):
    return dict(
        files=[],
        prompt="abstract waves",
        model="gemini-3.1-flash-image-preview",
        task="generate",
        format_output="text",
        aspect_ratio="1:1",
        num_images=1,
        size="1K",
        resolution="1080p",
        reference_images=None,
        output_file=str(tmp_path / "out.png"),
        verbose=False,
        dry_run=False,
    )


def _png_bytes() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def test_explicit_provider_codex_calls_codex_only(monkeypatch, base_kwargs, tmp_path):
    """--provider codex calls codex; never touches other providers."""
    called = {"codex": 0, "minimax": 0, "openrouter": 0, "imagen4": 0}

    def fake_codex(prompt, out_path, model=None, timeout=300):
        called["codex"] += 1
        Path(out_path).write_bytes(_png_bytes())
        return Path(out_path)

    monkeypatch.setattr(gbp, "generate_codex_image", fake_codex)
    monkeypatch.setattr(gbp, "generate_minimax_image",
                        lambda **kw: called.__setitem__("minimax", called["minimax"] + 1) or {"status": "success"})
    monkeypatch.setattr(gbp, "generate_openrouter_image",
                        lambda **kw: called.__setitem__("openrouter", called["openrouter"] + 1) or {"status": "success"})
    monkeypatch.setattr(gbp, "generate_image_imagen4",
                        lambda **kw: called.__setitem__("imagen4", called["imagen4"] + 1) or {"status": "success"})

    res = gbp.batch_process(provider="codex", **base_kwargs)
    assert called == {"codex": 1, "minimax": 0, "openrouter": 0, "imagen4": 0}
    assert res[0]["status"] == "success"
    assert res[0]["provider"] == "codex"


def test_codex_first_in_auto_succeeds(monkeypatch, base_kwargs):
    called = {"codex": 0, "google_branch": 0}

    def fake_codex(prompt, out_path, model=None, timeout=300):
        called["codex"] += 1
        Path(out_path).write_bytes(_png_bytes())
        return Path(out_path)

    def fake_google(*a, **kw):
        called["google_branch"] += 1
        return {"status": "success", "generated_images": ["/tmp/google.png"]}

    monkeypatch.setattr(gbp, "generate_codex_image", fake_codex)
    monkeypatch.setattr(gbp, "process_file", fake_google)
    monkeypatch.setattr(gbp, "generate_image_imagen4", fake_google)

    res = gbp.batch_process(provider="auto", **base_kwargs)
    assert called["codex"] == 1
    assert called["google_branch"] == 0
    assert res[0]["provider"] == "codex"


def test_quota_falls_through_to_google(monkeypatch, base_kwargs, tmp_path):
    called = {"codex": 0, "google_branch": 0}
    google_png = tmp_path / "g.png"

    def fake_codex(prompt, out_path, model=None, timeout=300):
        called["codex"] += 1
        raise cig.CodexQuotaExceeded("rate_limit_exceeded 429")

    def fake_process_file(*a, **kw):
        called["google_branch"] += 1
        google_png.write_bytes(_png_bytes())
        return {"status": "success", "generated_images": [str(google_png)], "model": "gemini-3.1-flash-image-preview"}

    monkeypatch.setattr(gbp, "generate_codex_image", fake_codex)
    monkeypatch.setattr(gbp, "process_file", fake_process_file)
    monkeypatch.setattr(gbp, "maybe_fallback_to_openrouter", lambda **kw: kw["result"])

    res = gbp.batch_process(provider="auto", **base_kwargs)
    assert called["codex"] == 1
    assert called["google_branch"] == 1
    assert res[0]["status"] == "success"


def test_codex_unavailable_silently_falls_through(monkeypatch, base_kwargs, capsys, tmp_path):
    google_png = tmp_path / "g.png"

    def fake_codex(prompt, out_path, model=None, timeout=300):
        raise cig.CodexNotAvailable("codex CLI not on PATH")

    def fake_process_file(*a, **kw):
        google_png.write_bytes(_png_bytes())
        return {"status": "success", "generated_images": [str(google_png)]}

    monkeypatch.setattr(gbp, "generate_codex_image", fake_codex)
    monkeypatch.setattr(gbp, "process_file", fake_process_file)
    monkeypatch.setattr(gbp, "maybe_fallback_to_openrouter", lambda **kw: kw["result"])

    res = gbp.batch_process(provider="auto", **base_kwargs)
    err = capsys.readouterr().err
    # Silent fallback (no '[auto] codex' line in non-verbose mode)
    assert "[auto] codex" not in err or "unavailable" not in err
    assert res[0]["status"] == "success"


def test_codex_explicit_no_fallback_on_quota(monkeypatch, base_kwargs):
    """--provider codex with quota error: returns error, does NOT fall through."""
    google_called = {"n": 0}

    def fake_codex(prompt, out_path, model=None, timeout=300):
        raise cig.CodexQuotaExceeded("429")

    monkeypatch.setattr(gbp, "generate_codex_image", fake_codex)
    monkeypatch.setattr(gbp, "process_file",
                        lambda **kw: google_called.__setitem__("n", google_called["n"] + 1) or {"status": "success"})

    res = gbp.batch_process(provider="codex", **base_kwargs)
    assert google_called["n"] == 0
    assert res[0]["status"] == "error"
    assert res[0]["error_kind"] == "codex_quota"


def test_codex_only_for_image_gen_not_video(monkeypatch, base_kwargs, tmp_path):
    """generate-video with --provider auto must NOT call codex."""
    base_kwargs["task"] = "generate-video"
    base_kwargs["model"] = "veo-3.1-generate-preview"
    veo_mp4 = tmp_path / "v.mp4"
    base_kwargs["output_file"] = str(veo_mp4)

    called = {"codex": 0, "veo": 0}

    def fake_codex(*a, **kw):
        called["codex"] += 1
        raise AssertionError("codex must not be called for video")

    veo_src = tmp_path / "veo_src.mp4"

    def fake_veo(*a, **kw):
        called["veo"] += 1
        veo_src.write_bytes(b"FAKE-MP4")
        return {"status": "success", "generated_video": str(veo_src)}

    monkeypatch.setattr(gbp, "generate_codex_image", fake_codex)
    monkeypatch.setattr(gbp, "generate_video_veo", fake_veo)

    res = gbp.batch_process(provider="auto", **base_kwargs)
    assert called["codex"] == 0
    assert called["veo"] == 1


def test_validate_skips_codex_models(monkeypatch):
    """validate_model_task_combination must accept any model when provider=codex."""
    # Should not raise for arbitrary model under --provider codex
    gbp.validate_model_task_combination("gpt-5.5", "generate", provider="codex")
    gbp.validate_model_task_combination("anything", "generate", provider="codex")


def test_provider_choices_include_codex():
    """Argparse --provider must include 'codex' as a valid choice."""
    assert "codex" in gbp.IMAGE_PROVIDER_VALUES
