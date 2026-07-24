#!/usr/bin/env python3
"""Codex CLI image-generation wrapper.

Shells out to `codex exec "$imagegen ..."` to generate images via the user's
ChatGPT subscription quota (no OPENAI_API_KEY required). Captures the produced
PNG from a tmpdir via filesystem glob (primary) and the agent's last message
written by `-o/--output-last-message` (secondary).

Custom exceptions are exported for the unified --provider switch in
gemini_batch_process.py to drive cascade fall-through.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_TIMEOUT = 600


class CodexError(Exception):
    """Generic Codex wrapper failure."""


class CodexNotAvailable(CodexError):
    """Codex CLI is not installed or the user is not logged in."""


class CodexQuotaExceeded(CodexError):
    """ChatGPT subscription quota exhausted (rate-limit / 429)."""


def check_codex_available() -> None:
    """Raise CodexNotAvailable if `codex` is missing or not logged in."""
    if shutil.which("codex") is None:
        raise CodexNotAvailable(
            "codex CLI not found on PATH. Install: brew install codex "
            "(or see https://developers.openai.com/codex/cli)."
        )
    try:
        proc = subprocess.run(
            ["codex", "login", "status"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise CodexNotAvailable(f"`codex login status` failed: {exc}") from exc

    combined = (proc.stdout or "") + (proc.stderr or "")
    if "Logged in using ChatGPT" not in combined:
        raise CodexNotAvailable(
            "Not logged in to Codex via ChatGPT. Run: codex login"
        )


_QUOTA_PATTERN = re.compile(r"\b(429|rate[ _-]?limit|quota|usage limit|too many requests)\b", re.IGNORECASE)


def _classify_failure(stdout: str, stderr: str, returncode: int) -> CodexError:
    blob = f"{stdout}\n{stderr}"
    if _QUOTA_PATTERN.search(blob):
        return CodexQuotaExceeded(
            f"Codex quota exceeded (exit {returncode}). Last message: "
            f"{(stderr or stdout).strip()[-400:]}"
        )
    return CodexError(
        f"codex exec failed (exit {returncode}). Last message: "
        f"{(stderr or stdout).strip()[-400:]}"
    )


def _newest_png(tmpdir: Path) -> Path | None:
    candidates = sorted(
        tmpdir.glob("*.png"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _path_from_last_message(last_msg_file: Path) -> Path | None:
    if not last_msg_file.exists():
        return None
    text = last_msg_file.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return None
    last_line = text.splitlines()[-1].strip()
    last_line = last_line.strip("`'\" ")
    if last_line and Path(last_line).is_file():
        return Path(last_line)
    return None


def generate_image(
    prompt: str,
    out_path: Path,
    model: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    images: list | None = None,
) -> Path:
    """Generate one image via Codex CLI, save to out_path, return out_path.

    Args:
        images: optional reference image path(s) attached via `codex exec -i`,
            enabling image-to-image / compositing (e.g. a logo onto a mockup).

    Raises:
        CodexNotAvailable: codex missing / not logged in.
        CodexQuotaExceeded: rate-limit / 429 detected in output.
        CodexError: any other non-zero exit, missing reference image, or no PNG captured.
    """
    check_codex_available()

    out_path = Path(out_path).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ref_images = []
    for img in (images or []):
        p = Path(img).expanduser().resolve()
        if not p.is_file():
            raise CodexError(f"reference image not found: {img}")
        ref_images.append(p)

    with tempfile.TemporaryDirectory(prefix="codex_imagegen_") as td:
        tmpdir = Path(td)
        last_msg = tmpdir / "last.txt"
        ref_note = (
            " Use the attached image(s) as the reference/source for the edit."
            if ref_images else ""
        )
        agent_prompt = (
            f"$imagegen {prompt}\n\n"
            f"Save the generated image to ./generated.png in the current directory.{ref_note} "
            "Output only the absolute file path on the last line."
        )
        cmd = [
            "codex", "exec",
            "--skip-git-repo-check",
            "--sandbox", "workspace-write",
            "-C", str(tmpdir),
            "-o", str(last_msg),
        ]
        for p in ref_images:
            cmd += ["-i", str(p)]
        if model:
            cmd += ["-m", model]
        # Prompt goes via stdin, NOT as a positional arg: `-i FILE...` is greedy
        # (nargs+) and would otherwise swallow a trailing prompt as another image.
        cmd.append("-")

        try:
            proc = subprocess.run(
                cmd,
                input=agent_prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise CodexError(f"codex exec timed out after {timeout}s") from exc
        except OSError as exc:
            raise CodexError(f"failed to launch codex exec: {exc}") from exc

        png = _newest_png(tmpdir)
        if png is None:
            png = _path_from_last_message(last_msg)
            if png and png.suffix.lower() != ".png":
                png = None

        if proc.returncode != 0 and png is None:
            raise _classify_failure(proc.stdout or "", proc.stderr or "", proc.returncode)

        if png is None:
            raise CodexError(
                "codex exec exited 0 but no PNG was produced. "
                f"stdout tail: {(proc.stdout or '').strip()[-400:]}"
            )

        shutil.copy2(png, out_path)
        if out_path.stat().st_size == 0:
            raise CodexError(f"captured image at {out_path} is empty")
        return out_path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="codex_imagegen.py",
        description="Generate images via Codex CLI ($imagegen) using ChatGPT subscription auth.",
    )
    p.add_argument("--prompt", required=True, help="Image description prompt.")
    p.add_argument("--out", required=True, help="Output PNG path.")
    p.add_argument(
        "--image", "-i",
        action="append",
        default=None,
        metavar="FILE",
        help="Reference image to attach (repeatable). Enables image-to-image / "
             "compositing, e.g. placing a logo onto a mockup.",
    )
    p.add_argument(
        "--model",
        default=None,
        help="Optional Codex base model (e.g. gpt-5.5). NOT the image model - "
             "image-model selection is internal to $imagegen.",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Subprocess timeout in seconds (default: {DEFAULT_TIMEOUT}).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        out = generate_image(
            prompt=args.prompt,
            out_path=Path(args.out),
            model=args.model,
            timeout=args.timeout,
            images=args.image,
        )
    except CodexNotAvailable as e:
        print(f"[codex] not available: {e}", file=sys.stderr)
        return 2
    except CodexQuotaExceeded as e:
        print(f"[codex] quota exceeded: {e}", file=sys.stderr)
        return 3
    except CodexError as e:
        print(f"[codex] error: {e}", file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
