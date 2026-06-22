#!/usr/bin/env python3
"""
Codex CLI image backend for vd:diagram.

Generates the diagram PNG via the Codex CLI's built-in image_gen tool
(gpt-image-2 family), billed to the user's ChatGPT subscription instead of the
OpenRouter image API. This is the DEFAULT image provider: it avoids per-image
OpenRouter spend (cost-optimized) and gpt-image-2 gives strong results.

Two hard-won prompt constraints are baked in:
- Force the bitmap image_gen path. Codex's imagegen skill otherwise routes
  "diagram" prompts to code/SVG rendering (its own "when not to use" rule),
  which silently bypasses the image model.
- Single generation pass. Dense diagram prompts make the agent loop spin
  (regenerate-and-critique) for many minutes; one pass keeps it bounded.

Public API mirrors openrouter_image.generate_image so generate.py can swap
providers without other changes.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import re
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "gpt-image-2 (codex subscription)"

_FORCE_PREFIX = (
    "Use your built-in image_gen tool to GENERATE one raster bitmap image in a "
    "SINGLE pass. Do NOT draw it with SVG, HTML, CSS, canvas, matplotlib or any "
    "code; do not iterate, critique, or regenerate — produce one image and stop. "
    "Save it to ./generated.png and output only its absolute path on the last line.\n\n"
)


class CodexImageError(RuntimeError):
    """Codex image generation failed (missing CLI, not logged in, timeout, no PNG)."""


def codex_available() -> bool:
    """True only if the codex CLI is installed AND logged in via ChatGPT."""
    if shutil.which("codex") is None:
        return False
    try:
        proc = subprocess.run(
            ["codex", "login", "status"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return "Logged in using ChatGPT" in ((proc.stdout or "") + (proc.stderr or ""))


def _newest_png(tmpdir: Path) -> Path | None:
    pngs = sorted(tmpdir.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    return pngs[0] if pngs else None


def _png_from_last_message(last_msg: Path) -> Path | None:
    if not last_msg.exists():
        return None
    text = last_msg.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return None
    candidates = [text.splitlines()[-1].strip().strip("`'\" ")]
    candidates.extend(match.group(0).strip("`'\" ") for match in re.finditer(r"[^\s`'\"]+\.png", text))
    for raw in candidates:
        candidate = Path(raw).expanduser()
        if candidate.is_file() and candidate.suffix.lower() == ".png":
            return candidate
    return None


def _codex_exec_cmd(tmpdir: Path, last_msg: Path, agent_prompt: str, reference_images: list[str] | None) -> list[str]:
    image_args = []
    for image in reference_images or []:
        resolved = Path(image).expanduser().resolve()
        if not resolved.is_file():
            raise CodexImageError(f"reference image not found: {image}")
        image_args.extend(["--image", str(resolved)])
    return [
        "codex", "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--ignore-rules",
        "--ignore-user-config",
        "--sandbox", "workspace-write",
        "-C", str(tmpdir),
        "-o", str(last_msg),
        *image_args,
        "--",
        agent_prompt,
    ]


def generate_image(
    prompt: str,
    output_path: str,
    model: str | None = None,
    aspect_ratio: str | None = None,
    quality: str | None = None,
    image_size: str | None = None,
    reference_images: list[str] | None = None,
    timeout: int = 900,
) -> dict[str, Any]:
    """Generate one image via Codex, save to output_path, return metadata.

    Signature-compatible with openrouter_image.generate_image. `quality` and
    `image_size` are accepted for parity and folded into the prompt hint.
    """
    if shutil.which("codex") is None:
        raise CodexImageError("codex CLI not found on PATH (brew install codex)")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    hint = ""
    if aspect_ratio:
        hint += f"Aspect ratio {aspect_ratio}. "
    if quality:
        hint += f"Quality: {quality}. "

    with tempfile.TemporaryDirectory(prefix="diagram_codex_") as td:
        tmpdir = Path(td)
        last_msg = tmpdir / "last.txt"
        agent_prompt = _FORCE_PREFIX + hint + prompt
        cmd = _codex_exec_cmd(tmpdir, last_msg, agent_prompt, reference_images)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise CodexImageError(f"codex exec timed out after {timeout}s") from exc
        except OSError as exc:
            raise CodexImageError(f"failed to launch codex exec: {exc}") from exc

        png = _newest_png(tmpdir) or _png_from_last_message(last_msg)
        if png is None:
            tail = (proc.stderr or proc.stdout or "").strip()[-300:]
            raise CodexImageError(
                f"no PNG produced (exit {proc.returncode}). codex tail: {tail}"
            )

        shutil.copy2(png, out)
        if out.stat().st_size == 0:
            raise CodexImageError(f"captured image at {out} is empty")

    return {"path": str(out), "bytes": out.stat().st_size, "model": model or DEFAULT_MODEL}


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("usage: codex_image.py <prompt> <output_path>", file=sys.stderr)
        sys.exit(2)
    print(generate_image(sys.argv[1], sys.argv[2]))
