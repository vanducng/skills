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
        "layer ordering, class names, hard rules. Use the style tokens for colors "
        "and typography, and composition rules for layout. Do not invent "
        "components not in the description."
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
