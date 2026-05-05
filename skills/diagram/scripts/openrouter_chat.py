#!/usr/bin/env python3
"""
Text-only OpenRouter chat completions for diagram-type classification,
prompt refinement, and SVG generation.
"""
from __future__ import annotations

import requests

from openrouter_image import OPENROUTER_API_URL, INSTALL_HINT, find_api_key

DEFAULT_MODEL = "anthropic/claude-haiku-4-5"


def chat(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
    timeout: int = 60,
) -> str:
    api_key = find_api_key()
    if not api_key:
        raise RuntimeError(INSTALL_HINT)
    res = requests.post(
        OPENROUTER_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/vanducng/skills",
            "X-Title": "vd:diagram",
        },
        json={"model": model, "messages": messages, "temperature": temperature},
        timeout=timeout,
    )
    if not res.ok:
        raise RuntimeError(f"OpenRouter chat HTTP {res.status_code}: {res.text[:500]}")
    return res.json()["choices"][0]["message"]["content"].strip()


def classify_type(description: str, available_types: list[str]) -> tuple[str, float]:
    types_str = ", ".join(available_types)
    system = (
        f"Classify the diagram type from this list: {types_str}. "
        "Reply with ONLY one of those exact strings on the first line. "
        "On the second line, write a confidence number 0.0–1.0. "
        "If unclear, pick the closest match with low confidence."
    )
    response = chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": description},
        ],
        temperature=0.1,
    )
    lines = [line.strip() for line in response.splitlines() if line.strip()]
    raw_type = lines[0].lower() if lines else ""
    chosen = next(
        (t for t in available_types if t.lower() == raw_type),
        None,
    )
    if chosen is None:
        chosen = next(
            (t for t in available_types if t.lower() in raw_type or raw_type in t.lower()),
            available_types[0],
        )
    confidence = 0.5
    if len(lines) >= 2:
        try:
            confidence = float(lines[1].split()[0])
        except (ValueError, IndexError):
            pass
    return chosen, confidence


def refine_prompt(
    description: str,
    type_ref: str,
    style_tokens: str,
    composition_rules: str,
    model: str = DEFAULT_MODEL,
) -> str:
    system = (
        "You are a diagram-prompt refiner. Read the user description and the "
        "style references below. Output a single-paragraph image-generation "
        "prompt that follows ALL the visual conventions, layout rules, and "
        "composition rules. Do not invent components not in the description. "
        "Output ONLY the refined prompt — no preamble, no markdown, no fences."
    )
    user = (
        f"## User description\n{description}\n\n"
        f"## Style tokens\n{style_tokens}\n\n"
        f"## Composition rules\n{composition_rules}\n\n"
        f"## Type-specific reference\n{type_ref}"
    )
    return chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model=model,
        temperature=0.2,
    )


def _strip_fences(raw: str) -> str:
    svg = raw.strip()
    for fence in ("```xml", "```svg", "```"):
        if svg.startswith(fence):
            svg = svg[len(fence) :].lstrip()
            break
    if svg.endswith("```"):
        svg = svg[:-3].rstrip()
    if not svg.lstrip().startswith("<svg"):
        raise RuntimeError(f"LLM did not return SVG markup. Got: {svg[:200]}")
    return svg


def generate_svg(
    description: str,
    type_ref: str,
    style_tokens: str,
    composition_rules: str,
    svg_contract: str,
    model: str = DEFAULT_MODEL,
) -> str:
    system = (
        "You output ONLY valid SVG 1.1 markup. No preamble, no markdown fences, "
        "no explanation. Follow the SVG contract exactly: required root attributes, "
        "layer ordering, class names, hard rules — especially the LAYOUT RULES "
        "(boundary tiling, orthogonal routing, label-inside-parent, bidirectional "
        "single-path with two markers, white-fill occlusion behind arrow labels). "
        "Walk the pre-flight checklist mentally before emitting. Use the style "
        "tokens for colors and typography, composition rules for layout. Do not "
        "invent components not in the description."
    )
    user = (
        f"## User description\n{description}\n\n"
        f"## Style tokens\n{style_tokens}\n\n"
        f"## Composition rules\n{composition_rules}\n\n"
        f"## SVG contract\n{svg_contract}\n\n"
        f"## Type-specific reference\n{type_ref}"
    )
    raw = chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model=model,
        temperature=0.3,
        timeout=120,
    )
    return _strip_fences(raw)


def revise_svg(
    draft_svg: str,
    description: str,
    svg_contract: str,
    model: str = DEFAULT_MODEL,
) -> str:
    """Critique-and-revise pass. Send the draft back, ask the LLM to find layout
    violations against the contract and emit a corrected SVG."""
    system = (
        "You are a layout critic for SVG diagrams. You will be given a draft SVG "
        "and the layout contract it must satisfy. Walk every check in the "
        "pre-flight checklist on the draft. Then output ONLY a corrected SVG 1.1 "
        "document — no markdown fences, no preamble, no explanation. If the draft "
        "is already perfect, re-emit it unchanged. Common defects to fix: "
        "(a) boundary rects that overlap each other, "
        "(b) text nodes outside their parent box, "
        "(c) boundary captions placed ABOVE their boundary instead of inside it, "
        "(d) connection lines that cross through a third box (replace with "
        "orthogonal polyline routed through the gutter), "
        "(e) two-arrow bidirectional pairs on the same line (collapse to one path "
        "with marker-start AND marker-end), "
        "(f) arrow labels missing the white-fill <rect> occluder behind them, "
        "(g) elements closer than 24px to a sibling. "
        "Preserve the original component set, palette, and class names — only fix "
        "geometry."
    )
    user = (
        f"## Original description\n{description}\n\n"
        f"## SVG contract (the rules that the draft must satisfy)\n{svg_contract}\n\n"
        f"## Draft SVG to revise\n{draft_svg}"
    )
    raw = chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model=model,
        temperature=0.1,
        timeout=120,
    )
    return _strip_fences(raw)
