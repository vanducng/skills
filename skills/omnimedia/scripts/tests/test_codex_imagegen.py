"""Mocked tests for codex_imagegen wrapper.

Live tests are gated behind OMNIMEDIA_SMOKE_CODEX=1 (skipped by default).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import codex_imagegen as cig  # noqa: E402


def test_check_codex_available_when_missing(monkeypatch):
    monkeypatch.setattr(cig.shutil, "which", lambda _: None)
    with pytest.raises(cig.CodexNotAvailable):
        cig.check_codex_available()


def test_check_codex_available_not_logged_in(monkeypatch):
    monkeypatch.setattr(cig.shutil, "which", lambda _: "/opt/homebrew/bin/codex")
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="Not logged in\n", stderr="")
    monkeypatch.setattr(cig.subprocess, "run", lambda *a, **kw: fake)
    with pytest.raises(cig.CodexNotAvailable):
        cig.check_codex_available()


def test_check_codex_available_ok(monkeypatch):
    monkeypatch.setattr(cig.shutil, "which", lambda _: "/opt/homebrew/bin/codex")
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="Logged in using ChatGPT\n", stderr="")
    monkeypatch.setattr(cig.subprocess, "run", lambda *a, **kw: fake)
    cig.check_codex_available()  # no raise


def test_generate_parses_quota_error(monkeypatch, tmp_path):
    monkeypatch.setattr(cig, "check_codex_available", lambda: None)

    fake = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr="error: 429 rate_limit_exceeded — quota exhausted",
    )
    monkeypatch.setattr(cig.subprocess, "run", lambda *a, **kw: fake)

    with pytest.raises(cig.CodexQuotaExceeded):
        cig.generate_image("a cube", tmp_path / "x.png")


def test_generate_generic_error(monkeypatch, tmp_path):
    monkeypatch.setattr(cig, "check_codex_available", lambda: None)
    fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="boom")
    monkeypatch.setattr(cig.subprocess, "run", lambda *a, **kw: fake)
    with pytest.raises(cig.CodexError) as excinfo:
        cig.generate_image("a cube", tmp_path / "x.png")
    assert not isinstance(excinfo.value, cig.CodexQuotaExceeded)


def test_generate_succeeds_via_filesystem_glob(monkeypatch, tmp_path):
    """Codex returns 0 and writes a PNG to tmpdir; wrapper copies it to out_path."""
    monkeypatch.setattr(cig, "check_codex_available", lambda: None)

    captured = {}

    def fake_run(cmd, *args, **kwargs):
        # Identify the tmpdir from -C flag and drop a fake PNG there.
        td = Path(cmd[cmd.index("-C") + 1])
        png = td / "generated.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="OK\n", stderr="")

    monkeypatch.setattr(cig.subprocess, "run", fake_run)

    out = cig.generate_image("a red cube", tmp_path / "result.png", model="gpt-5.5")
    assert out == (tmp_path / "result.png").resolve()
    assert out.read_bytes().startswith(b"\x89PNG")
    # Confirm CLI flags shape
    cmd = captured["cmd"]
    assert "--skip-git-repo-check" in cmd
    assert "--sandbox" in cmd and "workspace-write" in cmd
    assert "-m" in cmd and "gpt-5.5" in cmd


def test_generate_attaches_reference_images(monkeypatch, tmp_path):
    """images=[...] forwards each as `-i <path>` and notes the reference in the prompt."""
    monkeypatch.setattr(cig, "check_codex_available", lambda: None)
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)

    captured = {}

    def fake_run(cmd, *args, **kwargs):
        td = Path(cmd[cmd.index("-C") + 1])
        (td / "generated.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
        captured["cmd"] = cmd
        captured["input"] = kwargs.get("input")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="OK\n", stderr="")

    monkeypatch.setattr(cig.subprocess, "run", fake_run)

    cig.generate_image("place logo on card", tmp_path / "card.png", images=[str(logo)])
    cmd = captured["cmd"]
    assert "-i" in cmd and str(logo.resolve()) in cmd
    assert cmd[-1] == "-"  # prompt via stdin, not a positional (avoids -i greedy capture)
    assert "reference" in (captured["input"] or "")  # ref note injected into stdin prompt


def test_generate_missing_reference_image_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(cig, "check_codex_available", lambda: None)
    with pytest.raises(cig.CodexError):
        cig.generate_image("x", tmp_path / "out.png", images=[str(tmp_path / "nope.png")])


def test_generate_falls_back_to_last_message(monkeypatch, tmp_path):
    """No PNG in tmpdir, but last.txt contains a path to a real PNG elsewhere."""
    monkeypatch.setattr(cig, "check_codex_available", lambda: None)

    external_png = tmp_path / "elsewhere.png"
    external_png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

    def fake_run(cmd, *args, **kwargs):
        last_msg = Path(cmd[cmd.index("-o") + 1])
        last_msg.write_text(f"All done.\n{external_png}\n")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cig.subprocess, "run", fake_run)

    out = cig.generate_image("anything", tmp_path / "out.png")
    assert out.read_bytes().startswith(b"\x89PNG")


def test_generate_no_png_zero_exit_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(cig, "check_codex_available", lambda: None)
    monkeypatch.setattr(
        cig.subprocess, "run",
        lambda *a, **kw: subprocess.CompletedProcess(args=[], returncode=0, stdout="empty", stderr=""),
    )
    with pytest.raises(cig.CodexError):
        cig.generate_image("x", tmp_path / "out.png")


@pytest.mark.skipif(
    os.environ.get("OMNIMEDIA_SMOKE_CODEX") != "1",
    reason="live smoke disabled (set OMNIMEDIA_SMOKE_CODEX=1 to enable)",
)
def test_live_codex_generation(tmp_path):
    out = cig.generate_image(
        "A simple red cube on a white background, photorealistic",
        tmp_path / "live.png",
        timeout=180,
    )
    assert out.exists() and out.stat().st_size > 0
    assert out.read_bytes().startswith(b"\x89PNG")
