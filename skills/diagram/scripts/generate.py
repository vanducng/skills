#!/usr/bin/env python3
"""
vd:diagram — generate diagrams from natural-language descriptions via OpenRouter.

Run with:  ~/.claude/skills/.venv/bin/python3 scripts/generate.py "<description>"
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from openrouter_chat import (
    DEFAULT_MODEL as REFINE_MODEL,
    classify_type,
    generate_skeleton,
    generate_svg,
    paint_svg,
    refine_prompt,
    revise_svg,
)
from openrouter_image import DEFAULT_MODEL as IMAGE_MODEL
from openrouter_image import find_api_key, generate_image
from codex_image import (
    DEFAULT_MODEL as CODEX_IMAGE_MODEL,
    CodexImageError,
    codex_available,
    generate_image as codex_generate_image,
)
from skeleton_layout import laid_out_to_yaml, layered_lr
from skeleton_schema import SkeletonError, parse_skeleton
from validation import ExpectedLayout, validate_and_fix

SUPPORTED_TYPES = [
    "system-architecture",
    "data-flow",
    "workflow",
    "sequence",
    "er-diagram",
    "state-machine",
    "c4-context",
    "c4-container",
]

TYPE_ALIASES = {
    "arch": "system-architecture",
    "flow": "data-flow",
    "wf": "workflow",
    "process": "workflow",
    "seq": "sequence",
    "er": "er-diagram",
    "state": "state-machine",
    "c4": "c4-context",
}

SUPPORTED_PRESETS = ["warm", "mono", "pastel", "cyberpunk"]
DEFAULT_PRESET = "warm"

SUPPORTED_ENGINES = ["free", "skeleton"]

# Default engine per type. Free is the fallback for types skeleton can't model.
ENGINE_DEFAULT_BY_TYPE = {
    "system-architecture": "skeleton",
    "data-flow":           "skeleton",
    "workflow":            "skeleton",
    "c4-context":          "skeleton",
    "c4-container":        "skeleton",
    "er-diagram":          "skeleton",
    "sequence":            "free",
    "state-machine":       "free",
}


# ---------------------------------------------------------------------------
# Path & filesystem helpers
# ---------------------------------------------------------------------------


def find_skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def find_git_root(start: Path | None = None) -> Path | None:
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def find_file_browser_server() -> Path | None:
    primary = find_skill_root().parent / "file-browser" / "scripts" / "server.cjs"
    if primary.exists():
        return primary
    home_path = Path(os.environ.get("HOME", "")) / "skills/skills/file-browser/scripts/server.cjs"
    if home_path.exists():
        return home_path
    return None


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s or "diagram")[:40].rstrip("-")


def resolve_output_dir(slug: str) -> tuple[Path, Path]:
    """Return (parent_diagrams_dir, session_dir)."""
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M")
    git_root = find_git_root()
    if git_root:
        parent = git_root / ".diagrams"
    else:
        parent = Path.home() / "Documents" / "llm-diagrams" / Path.cwd().name
    session = parent / f"{stamp}-{slug}"
    if session.exists():
        session = parent / f"{stamp}{_dt.datetime.now().strftime('%S')}-{slug}"
    session.mkdir(parents=True, exist_ok=True)
    return parent, session


def resolve_versioned_output_dir(slug: str) -> tuple[Path, Path]:
    """Return a stable, git-trackable diagram directory under docs/diagrams."""
    git_root = find_git_root()
    if git_root is None:
        raise RuntimeError("--versioned requires running inside a git repository")
    parent = git_root / "docs" / "diagrams"
    session = parent / slug
    session.mkdir(parents=True, exist_ok=True)
    return parent, session


def ensure_self_ignore(parent_diagrams_dir: Path) -> None:
    if find_git_root() is None:
        return
    gitignore = parent_diagrams_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n!.gitignore\n")


# ---------------------------------------------------------------------------
# Reference loading
# ---------------------------------------------------------------------------


def load_refs(
    diagram_type: str,
    want_svg: bool,
    preset: str = DEFAULT_PRESET,
    *,
    want_skeleton: bool = False,
) -> dict[str, str]:
    refs_dir = find_skill_root() / "references"
    preset_tokens = refs_dir / "presets" / preset / "style-tokens.md"
    if not preset_tokens.exists():
        raise RuntimeError(f"unknown preset: {preset!r} (no {preset_tokens})")
    out = {
        "style_tokens": preset_tokens.read_text(),
        "style_foundations": (refs_dir / "style-foundations.md").read_text(),
        "composition_rules": (refs_dir / "composition-rules.md").read_text(),
        "type_ref": (refs_dir / "types" / f"{diagram_type}.md").read_text(),
    }
    if want_svg:
        out["svg_contract"] = (refs_dir / "svg-contract.md").read_text()
    if want_skeleton:
        out["skeleton_contract"] = (refs_dir / "skeleton-contract.md").read_text()
        out["painter_contract"] = (refs_dir / "painter-contract.md").read_text()
    return out


# ---------------------------------------------------------------------------
# Session metadata + iteration helpers
# ---------------------------------------------------------------------------


def find_latest_session(parent_diagrams_dir: Path) -> Path | None:
    if not parent_diagrams_dir.exists():
        return None
    sessions = [p for p in parent_diagrams_dir.iterdir() if p.is_dir()]
    if not sessions:
        return None
    return max(sessions, key=lambda p: p.stat().st_mtime)


def next_variant_index(session_dir: Path, fmt: str) -> int:
    pattern = re.compile(r"^v(\d+)\.")
    indices = []
    for p in session_dir.glob(f"v*.{fmt}"):
        m = pattern.match(p.name)
        if m:
            indices.append(int(m.group(1)))
    return (max(indices) + 1) if indices else 1


def read_session_meta(session_dir: Path) -> dict | None:
    meta_path = session_dir / "meta.json"
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def write_session_artifacts(
    session_dir: Path,
    *,
    original: str,
    refined: str,
    image_path: Path,
    diagram_type: str,
    fmt: str,
    refine_model: str,
    image_model: str | None,
    quality: str,
    aspect_ratio: str,
    preset: str,
    engine: str | None = None,
) -> None:
    refined_for_md = refined if len(refined) <= 1000 else f"{refined[:1000]}\n... ({len(refined)} chars total)"
    prompt_md = (
        f"## Original\n{original}\n\n"
        f"## Preset\n{preset}\n\n"
        f"## Refined\n{refined_for_md}\n\n"
        f"## Image model\n{image_model or '(SVG-only run, no image-gen model)'}\n\n"
        f"## Image\n{image_path.name}\n"
    )
    (session_dir / "prompt.md").write_text(prompt_md)
    meta = {
        "created": _dt.datetime.now().isoformat(timespec="seconds"),
        "type": diagram_type,
        "format": fmt,
        "preset": preset,
        "model": image_model or refine_model,
        "refine_model": refine_model,
        "quality": quality,
        "aspect_ratio": aspect_ratio,
        "original_description": original,
        "image_files": [image_path.name],
    }
    if engine is not None:
        meta["engine"] = engine
    (session_dir / "meta.json").write_text(json.dumps(meta, indent=2))


def append_iteration(
    session_dir: Path,
    *,
    feedback: str,
    refined: str,
    image_path: Path,
    variant: int,
) -> None:
    refined_for_md = refined if len(refined) <= 1000 else f"{refined[:1000]}\n... ({len(refined)} chars total)"
    section = (
        f"\n\n## Iteration v{variant}\n"
        f"**Feedback:** {feedback}\n\n"
        f"**Refined:**\n{refined_for_md}\n\n"
        f"**File:** {image_path.name}\n"
    )
    prompt_md = session_dir / "prompt.md"
    prompt_md.write_text(prompt_md.read_text() + section)
    meta_path = session_dir / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        meta.setdefault("image_files", []).append(image_path.name)
        meta_path.write_text(json.dumps(meta, indent=2))


def _yaml_block(text: str, indent: str = "  ") -> str:
    lines = (text or "").splitlines() or [""]
    return "\n".join(f"{indent}{line}" for line in lines)


def write_versioned_spec(
    session_dir: Path,
    *,
    slug: str,
    original: str,
    diagram_type: str,
    fmt: str,
    preset: str,
    engine: str,
    image_path: Path,
) -> None:
    """Write a small reviewable source spec beside the rendered variant."""
    spec = (
        "schema_version: 1\n"
        "kind: vd.diagram\n"
        f"slug: {slug}\n"
        f"type: {diagram_type}\n"
        f"format: {fmt}\n"
        f"preset: {preset}\n"
        f"engine: {engine}\n"
        f"latest: {image_path.name}\n"
        "description: |-\n"
        f"{_yaml_block(original)}\n"
    )
    (session_dir / "diagram.spec.yaml").write_text(spec)


def write_versioned_manifest(
    session_dir: Path,
    *,
    slug: str,
    diagram_type: str,
    fmt: str,
    preset: str,
    engine: str,
    image_path: Path,
) -> None:
    """Write deterministic metadata for git diffs and automation."""
    variants = sorted(p.name for p in session_dir.glob("v*.*") if p.suffix in {".svg", ".png"})
    manifest = {
        "schema_version": 1,
        "kind": "vd.diagram.manifest",
        "slug": slug,
        "type": diagram_type,
        "format": fmt,
        "preset": preset,
        "engine": engine,
        "latest": image_path.name,
        "variants": variants,
    }
    (session_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def print_output_handoff(output_path: Path, session_dir: Path, *, versioned: bool = False) -> None:
    """Print openable absolute locations for the generated diagram artifacts."""
    resolved_output = output_path.resolve()
    resolved_session = session_dir.resolve()
    print(f"→ saved: {resolved_output}", flush=True)
    print(f"→ file URI: {resolved_output.as_uri()}", flush=True)
    print(f"→ session dir: {resolved_session}", flush=True)
    if versioned:
        for name in ("diagram.spec.yaml", "manifest.json"):
            companion = session_dir / name
            if companion.exists():
                resolved_companion = companion.resolve()
                print(f"→ companion: {resolved_companion}", flush=True)
                print(f"→ companion URI: {resolved_companion.as_uri()}", flush=True)


# ---------------------------------------------------------------------------
# Viewer
# ---------------------------------------------------------------------------


def spawn_viewer(parent_diagrams_dir: Path, open_browser: bool) -> str | None:
    server = find_file_browser_server()
    if server is None:
        print(
            "warning: file-browser server not found. "
            "Install with: cd $HOME/skills/skills/file-browser && npm install",
            file=sys.stderr,
        )
        return None
    cmd = ["node", str(server), "--dir", str(parent_diagrams_dir), "--background"]
    if not open_browser:
        cmd.append("--no-open")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            print(f"warning: file-browser exit {proc.returncode}: {proc.stderr.strip()}", file=sys.stderr)
            return None
        envelope = json.loads(proc.stdout.strip().splitlines()[-1])
        return envelope.get("url")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        print(f"warning: file-browser spawn failed: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="generate.py",
        description="Generate a diagram from a natural-language description via OpenRouter.",
    )
    parser.add_argument("description", nargs="?", default=None, help="Natural-language diagram description.")
    parser.add_argument(
        "--type",
        dest="type",
        choices=SUPPORTED_TYPES + list(TYPE_ALIASES.keys()),
        default=None,
        help="Diagram type. Auto-classified if omitted.",
    )
    parser.add_argument("--format", choices=["png", "svg"], default="png")
    parser.add_argument(
        "--provider",
        choices=["codex", "openrouter"],
        default="codex",
        help=(
            "PNG image provider. codex (default): gpt-image-2 via Codex CLI / "
            "ChatGPT subscription — cost-optimized, falls back to OpenRouter if "
            "codex is unavailable. openrouter: gpt-5.4-image-2 via OpenRouter API."
        ),
    )
    parser.add_argument("--quality", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--aspect-ratio", default="16:9")
    parser.add_argument("--no-open", action="store_true", help="Do not auto-open the browser.")
    parser.add_argument("--slug", default=None, help="Override slug for the session dir name.")
    parser.add_argument("--regen", default=None, help="Regenerate latest session with feedback applied.")
    parser.add_argument("--new", action="store_true", help="Force a fresh session dir.")
    parser.add_argument(
        "--preset",
        choices=SUPPORTED_PRESETS,
        default=DEFAULT_PRESET,
        help="Visual style preset (default: warm).",
    )
    parser.add_argument(
        "--no-revise",
        action="store_true",
        help="Skip the SVG critique/revise pass (faster, lower quality).",
    )
    parser.add_argument(
        "--engine",
        choices=SUPPORTED_ENGINES,
        default=None,
        help=("free: pure-LLM SVG path (current default for sequence/state-machine). "
              "skeleton: two-pass YAML → layout → paint. "
              "Default depends on --type."),
    )
    parser.add_argument(
        "--versioned",
        action="store_true",
        help=(
            "Write git-trackable artifacts under docs/diagrams/<slug>/ "
            "with diagram.spec.yaml, manifest.json, and vN.<format> variants."
        ),
    )
    return parser.parse_args(argv)


def resolve_engine(arg_engine: str | None, diagram_type: str, fmt: str) -> str:
    if fmt != "svg":
        return "free"  # PNG path is never skeleton
    engine = arg_engine or ENGINE_DEFAULT_BY_TYPE.get(diagram_type, "free")
    if engine == "skeleton" and ENGINE_DEFAULT_BY_TYPE.get(diagram_type) != "skeleton":
        raise RuntimeError(
            f"--engine skeleton not supported for type {diagram_type!r}. "
            f"Skeleton types: "
            f"{sorted(t for t, e in ENGINE_DEFAULT_BY_TYPE.items() if e == 'skeleton')}"
        )
    return engine


def _resolve_type(arg_type: str | None, description: str) -> tuple[str, float]:
    if arg_type:
        resolved = TYPE_ALIASES.get(arg_type, arg_type)
        return resolved, 1.0
    print("→ classifying type…", flush=True)
    return classify_type(description, SUPPORTED_TYPES)


def _resolve_parent_dir(versioned: bool = False) -> Path:
    if versioned:
        git_root = find_git_root()
        if git_root is None:
            raise RuntimeError("--versioned requires running inside a git repository")
        return git_root / "docs" / "diagrams"
    git_root = find_git_root()
    if git_root:
        return git_root / ".diagrams"
    return Path.home() / "Documents" / "llm-diagrams" / Path.cwd().name


def _produce_svg_free(
    *,
    description: str,
    output_path: Path,
    refs: dict[str, str],
    style_tokens: str,
    preset: str,
    revise: bool = True,
) -> tuple[str, str | None]:
    """Pure-LLM SVG path. UNCHANGED from pre-skeleton-engine behavior."""
    print(f"→ generating SVG draft (preset: {preset}, model: {REFINE_MODEL}, ~10–20s)…", flush=True)
    svg_text = generate_svg(
        description=description,
        type_ref=refs["type_ref"],
        style_tokens=style_tokens,
        composition_rules=refs["composition_rules"],
        svg_contract=refs["svg_contract"],
    )
    if revise:
        print(f"→ critiquing + revising layout (~10–20s)…", flush=True)
        svg_text = revise_svg(
            draft_svg=svg_text,
            description=description,
            svg_contract=refs["svg_contract"],
        )
    svg_text, vreport = validate_and_fix(svg_text)
    for fix in vreport.autofix_applied:
        print(f"→ validation auto-fix: {fix}", flush=True)
    if vreport.needs_revise and revise:
        print(f"→ validation found {len(vreport.blocking_issues)} issue(s); revising once more…", flush=True)
        svg_text = revise_svg(
            draft_svg=svg_text,
            description=description,
            svg_contract=refs["svg_contract"],
            extra_feedback=vreport.summary(),
        )
        svg_text, vreport2 = validate_and_fix(svg_text)
        for fix in vreport2.autofix_applied:
            print(f"→ validation auto-fix (post-revise): {fix}", flush=True)
        if vreport2.needs_revise:
            print(f"⚠ validation still flags {len(vreport2.blocking_issues)} issue(s); writing anyway", flush=True)
    output_path.write_text(svg_text)
    return svg_text, None


def _produce_svg_skeleton(
    *,
    description: str,
    diagram_type: str,
    preset: str,
    output_path: Path,
    refs: dict[str, str],
    revise: bool = True,
) -> tuple[str, str | None]:
    skel = _generate_valid_skeleton(
        description=description,
        diagram_type=diagram_type,
        preset=preset,
        refs=refs,
    )

    print(f"→ laying out: {len(skel.elements)} elements, {len(skel.edges)} edges, "
          f"{len(skel.groups)} groups…", flush=True)
    laid = layered_lr(skel)
    expected = ExpectedLayout(nodes={n: t for n, t in laid.nodes.items()})

    print(f"→ pass 2: painting SVG (canvas {laid.canvas_w}×{laid.canvas_h})…", flush=True)
    svg_text = paint_svg(
        laid_out_yaml=laid_out_to_yaml(laid),
        description=description,
        preset_tokens=refs["style_tokens"],
        style_foundations=refs["style_foundations"],
        composition_rules=refs["composition_rules"],
        svg_contract=refs["svg_contract"],
        painter_contract=refs["painter_contract"],
    )

    svg_text, vreport = validate_and_fix(svg_text, expected_layout=expected)
    for fix in vreport.autofix_applied:
        print(f"→ validation auto-fix: {fix}", flush=True)

    if vreport.needs_revise and revise:
        print(f"→ {len(vreport.blocking_issues)} issue(s); one revise pass…", flush=True)
        coords_locked_banner = (
            "COORDINATES ARE LOCKED — DO NOT MOVE, RESIZE, OR REORDER ANY "
            "ELEMENT. Resolve issues only via colors / line weights / decoration / "
            "<style> changes. Preserve every (x, y, width, height) and every "
            "data-name/data-bbox attribute exactly as supplied.\n\n"
        )
        svg_text = revise_svg(
            draft_svg=svg_text,
            description=description,
            svg_contract=refs["svg_contract"],
            extra_feedback=coords_locked_banner + vreport.summary(),
        )
        svg_text, vreport2 = validate_and_fix(svg_text, expected_layout=expected)
        for fix in vreport2.autofix_applied:
            print(f"→ validation auto-fix (post-revise): {fix}", flush=True)
        if vreport2.needs_revise:
            print(f"⚠ still {len(vreport2.blocking_issues)} issue(s); writing anyway", flush=True)

    output_path.write_text(svg_text)
    return svg_text, None


def _generate_valid_skeleton(
    *,
    description: str,
    diagram_type: str,
    preset: str,
    refs: dict[str, str],
):
    """Emit and validate pass-1 YAML, retrying once with validator feedback."""
    last_error: SkeletonError | None = None
    for attempt in range(1, 3):
        suffix = "" if last_error is None else (
            "\n\nPrevious YAML failed validation. Fix this exact issue and keep "
            f"all labels short enough for the schema: {last_error}"
        )
        print(
            f"→ pass 1: emitting skeleton attempt {attempt}/2 "
            f"(preset: {preset}, model: {REFINE_MODEL})…",
            flush=True,
        )
        skel_yaml = generate_skeleton(
            description=description + suffix,
            diagram_type=diagram_type,
            preset=preset,
            skeleton_contract=refs["skeleton_contract"],
            type_ref=refs["type_ref"],
        )
        try:
            return parse_skeleton(skel_yaml)
        except SkeletonError as exc:
            last_error = exc
            if attempt == 1:
                print(f"→ pass 1 validation failed: {exc}; retrying once…", flush=True)
    raise RuntimeError(f"pass-1 emitted invalid skeleton after retry: {last_error}") from last_error


def _produce_image(
    *,
    description: str,
    diagram_type: str,
    fmt: str,
    quality: str,
    aspect_ratio: str,
    output_path: Path,
    preset: str,
    revise: bool = True,
    engine: str = "free",
    image_provider: str = "codex",
) -> tuple[str, str]:
    """Return (refined_text_or_svg, image_model_or_none)."""
    want_skeleton = (fmt == "svg" and engine == "skeleton")
    refs = load_refs(
        diagram_type, want_svg=(fmt == "svg"), preset=preset,
        want_skeleton=want_skeleton,
    )
    style_tokens = (
        f"# Active preset: {preset}\n\n"
        f"## Preset style-tokens\n{refs['style_tokens']}\n\n"
        f"## Style foundations (theme-agnostic)\n{refs['style_foundations']}"
    )
    if fmt == "svg":
        if engine == "skeleton":
            return _produce_svg_skeleton(
                description=description, diagram_type=diagram_type, preset=preset,
                output_path=output_path, refs=refs, revise=revise,
            )
        return _produce_svg_free(
            description=description, output_path=output_path,
            refs=refs, style_tokens=style_tokens, preset=preset, revise=revise,
        )
    print(f"→ refining prompt (preset: {preset}, model: {REFINE_MODEL}, ~5–10s)…", flush=True)
    refined = refine_prompt(
        description=description,
        type_ref=refs["type_ref"],
        style_tokens=style_tokens,
        composition_rules=refs["composition_rules"],
    )
    if image_provider == "codex":
        if codex_available():
            print(f"→ generating PNG via codex ({CODEX_IMAGE_MODEL}, ~30–120s)…", flush=True)
            try:
                codex_generate_image(
                    prompt=refined,
                    output_path=str(output_path),
                    aspect_ratio=aspect_ratio,
                    quality=quality,
                )
                return refined, CODEX_IMAGE_MODEL
            except CodexImageError as exc:
                print(f"⚠ codex image failed ({exc}); falling back to OpenRouter", file=sys.stderr, flush=True)
        else:
            print("⚠ codex unavailable (not installed / not logged in); using OpenRouter", file=sys.stderr, flush=True)

    print(f"→ generating PNG (model: {IMAGE_MODEL}, ~30–90s)…", flush=True)
    generate_image(
        prompt=refined,
        output_path=str(output_path),
        aspect_ratio=aspect_ratio,
        quality=quality,
    )
    return refined, IMAGE_MODEL


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    print("→ resolving config…", flush=True)
    if find_api_key() is None:
        print(
            "OPEN_ROUTER_KEY (or OPENROUTER_API_KEY) not set. "
            "Get a key at https://openrouter.ai/settings/keys",
            file=sys.stderr,
        )
        return 1

    parent_dir = _resolve_parent_dir(versioned=args.versioned)
    parent_dir.mkdir(parents=True, exist_ok=True)
    if not args.versioned:
        ensure_self_ignore(parent_dir)

    # Branch: --regen
    if args.regen:
        session_dir = find_latest_session(parent_dir)
        if session_dir is None:
            print(
                "no prior session — drop --regen and pass a description",
                file=sys.stderr,
            )
            return 1
        meta = read_session_meta(session_dir) or {}
        if args.description:
            print(
                "warning: ignoring positional description; --regen uses the prior session's description",
                file=sys.stderr,
            )
        original = meta.get("original_description")
        if not original:
            print(
                "warning: legacy session without original_description; using --regen feedback as description",
                file=sys.stderr,
            )
            original = args.regen
        diagram_type = meta.get("type") or "system-architecture"
        fmt = meta.get("format") or args.format
        preset = meta.get("preset") or args.preset
        engine = meta.get("engine") or resolve_engine(args.engine, diagram_type, fmt)
        effective = f"{original}\n\nFeedback for next iteration: {args.regen}"
        variant = next_variant_index(session_dir, fmt)
        out_path = session_dir / f"v{variant}.{fmt}"
        print(
            f"→ regen: session={session_dir.name}, type={diagram_type}, format={fmt}, "
            f"preset={preset}, engine={engine}, variant=v{variant}",
            flush=True,
        )
        refined, _img_model = _produce_image(
            description=effective,
            diagram_type=diagram_type,
            fmt=fmt,
            quality=args.quality,
            aspect_ratio=args.aspect_ratio,
            output_path=out_path,
            engine=engine,
            preset=preset,
            revise=not args.no_revise,
            image_provider=args.provider,
        )
        append_iteration(
            session_dir,
            feedback=args.regen,
            refined=refined,
            image_path=out_path,
            variant=variant,
        )
        if args.versioned or meta.get("versioned"):
            write_versioned_spec(
                session_dir,
                slug=session_dir.name,
                original=original,
                diagram_type=diagram_type,
                fmt=fmt,
                preset=preset,
                engine=engine,
                image_path=out_path,
            )
            write_versioned_manifest(
                session_dir,
                slug=session_dir.name,
                diagram_type=diagram_type,
                fmt=fmt,
                preset=preset,
                engine=engine,
                image_path=out_path,
            )
        print_output_handoff(out_path, session_dir, versioned=args.versioned or bool(meta.get("versioned")))
        print("→ spawning gallery…", flush=True)
        url = spawn_viewer(parent_dir, open_browser=not args.no_open)
        if url:
            print(f"✓ {url}")
        return 0

    # Default + --new branches require a description
    if not args.description:
        print(
            "no description and no --regen — pass a description or use --regen with feedback",
            file=sys.stderr,
        )
        return 1

    diagram_type, confidence = _resolve_type(args.type, args.description)
    if args.type is None:
        print(f"→ type: {diagram_type} (confidence {confidence:.2f})", flush=True)
        if confidence < 0.6:
            print(f"  (low confidence — pass --type to override; choices: {', '.join(SUPPORTED_TYPES)})", flush=True)
    else:
        print(f"→ type: {diagram_type}", flush=True)

    engine = resolve_engine(args.engine, diagram_type, args.format)
    print(f"→ engine: {engine}", flush=True)

    slug = args.slug or slugify(f"{diagram_type}-{args.description}")
    if args.versioned:
        _, session_dir = resolve_versioned_output_dir(slug)
        variant = next_variant_index(session_dir, args.format)
        out_path = session_dir / f"v{variant}.{args.format}"
    else:
        _, session_dir = resolve_output_dir(slug)
        variant = 1
        out_path = session_dir / f"v1.{args.format}"

    refined, image_model = _produce_image(
        description=args.description,
        diagram_type=diagram_type,
        fmt=args.format,
        quality=args.quality,
        aspect_ratio=args.aspect_ratio,
        output_path=out_path,
        preset=args.preset,
        revise=not args.no_revise,
        engine=engine,
        image_provider=args.provider,
    )
    if variant == 1 or not (session_dir / "prompt.md").exists():
        write_session_artifacts(
            session_dir,
            original=args.description,
            refined=refined,
            image_path=out_path,
            diagram_type=diagram_type,
            fmt=args.format,
            refine_model=REFINE_MODEL,
            image_model=image_model,
            quality=args.quality,
            aspect_ratio=args.aspect_ratio,
            preset=args.preset,
            engine=engine,
        )
    else:
        append_iteration(
            session_dir,
            feedback="new versioned variant",
            refined=refined,
            image_path=out_path,
            variant=variant,
        )

    if args.versioned:
        meta_path = session_dir / "meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            meta["versioned"] = True
            meta_path.write_text(json.dumps(meta, indent=2))
        write_versioned_spec(
            session_dir,
            slug=slug,
            original=args.description,
            diagram_type=diagram_type,
            fmt=args.format,
            preset=args.preset,
            engine=engine,
            image_path=out_path,
        )
        write_versioned_manifest(
            session_dir,
            slug=slug,
            diagram_type=diagram_type,
            fmt=args.format,
            preset=args.preset,
            engine=engine,
            image_path=out_path,
        )

    print_output_handoff(out_path, session_dir, versioned=args.versioned)

    print("→ spawning gallery…", flush=True)
    url = spawn_viewer(parent_dir, open_browser=not args.no_open)
    if url:
        print(f"✓ {url}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
