#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Codex gpt-image-2 front-door for marketing-design generators.

Default image-gen engine. Delegates to the `omnimedia` skill's
`codex_imagegen.py`, which drives Codex's `$imagegen` ($imagegen picks
gpt-image-2 internally) on the user's ChatGPT subscription - no API key.

Reuses the tested wrapper rather than reimplementing the codex exec / PNG
capture logic. See omnimedia/references/codex-imagegen.md.

Note: Codex `$imagegen` is text->image only (no input-image conditioning),
so logo-on-mockup compositing (CIP) must use Gemini instead.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


class CodexUnavailable(RuntimeError):
    """omnimedia's codex wrapper is missing, or codex failed / hit quota."""


def _wrapper() -> Path | None:
    """Locate omnimedia's codex_imagegen.py (installed symlink or repo layout)."""
    candidates = [
        Path.home() / ".claude" / "skills" / "omnimedia" / "scripts" / "codex_imagegen.py",
        Path(__file__).resolve().parents[2] / "omnimedia" / "scripts" / "codex_imagegen.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def available() -> bool:
    return _wrapper() is not None


def generate(
    prompt: str,
    out_path,
    *,
    aspect_ratio: str | None = None,
    images: list | None = None,
    timeout: int = 600,
) -> str:
    """Generate one image via Codex gpt-image-2. Return out_path, or raise CodexUnavailable.

    images: optional reference image path(s) (e.g. a logo) attached for
    image-to-image / compositing. Requires codex-cli >= 0.137.
    """
    wrapper = _wrapper()
    if wrapper is None:
        raise CodexUnavailable(
            "omnimedia codex_imagegen.py not found - install the omnimedia skill, "
            "or pass --provider gemini."
        )
    if aspect_ratio:
        prompt = f"{prompt}\n\nComposition: {aspect_ratio} aspect ratio."
    out = str(Path(out_path).expanduser())
    cmd = [sys.executable, str(wrapper), "--prompt", prompt, "--out", out, "--timeout", str(timeout)]
    for img in (images or []):
        cmd += ["--image", str(img)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-300:]
        raise CodexUnavailable(f"codex exit {proc.returncode}: {tail}")
    return out
