---
name: diagram
description: "Generate modern reviewable diagrams (system architecture, workflow, data flow, sequence, ER, state-machine, C4) via OpenRouter image-gen or LLM-emitted SVG. Auto-classifies diagram type from prompt; --type to override. Default outputs to <git-root>/.diagrams/; --versioned writes git-trackable specs and variants under docs/diagrams/."
license: MIT
argument-hint: "[description] [--type TYPE] [--preset PRESET] [--format png|svg] [--versioned] [--regen FEEDBACK] [--new]"
metadata:
  author: vanducng
  version: "0.5.0"
---

# vd:diagram

Turn natural-language descriptions into reviewable diagram images and version-controlled diagram artifacts. Two render paths:
- **PNG** (default): refines the prompt with `claude-haiku-4-5`, hands it to `gpt-5.4-image-2` for image generation.
- **SVG** (`--format svg`): the LLM emits the SVG markup directly. Cheaper, crisper labels, hand-editable.

Use `--versioned` when the diagram belongs in docs, ADRs, specs, or PR review. It writes a stable folder under `docs/diagrams/<slug>/` with:
- `diagram.spec.yaml` — reviewable source intent (type, preset, engine, description, latest variant)
- `manifest.json` — deterministic metadata for automation
- `v1.svg`, `v2.svg`, ... or `v1.png`, `v2.png`, ... — rendered variants

## Quick Start

```bash
# Auto-detect type, default PNG
~/.claude/skills/.venv/bin/python3 $HOME/skills/skills/diagram/scripts/generate.py \
  "system architecture for an OAuth signup flow with FastAPI backend"

# Explicit type, SVG output
~/.claude/skills/.venv/bin/python3 $HOME/skills/skills/diagram/scripts/generate.py \
  --type sequence --format svg \
  "user logs in: User → App → Auth Provider → callback"

# Version-controlled workflow artifact for docs/diagrams/
~/.claude/skills/.venv/bin/python3 $HOME/skills/skills/diagram/scripts/generate.py \
  --type workflow --format svg --versioned --slug checkout-fulfillment \
  "checkout workflow from cart review through payment, fraud check, warehouse pick, and shipment"

# Iterate on the latest diagram with feedback
~/.claude/skills/.venv/bin/python3 $HOME/skills/skills/diagram/scripts/generate.py \
  --regen "make the auth box use the warning color"

# Pick a different visual style preset (cyberpunk for talk slides)
~/.claude/skills/.venv/bin/python3 $HOME/skills/skills/diagram/scripts/generate.py \
  --preset cyberpunk \
  "data flow: Kafka → Spark → ClickHouse → Grafana"
```

## Setup

```bash
export OPEN_ROUTER_KEY="sk-or-v1-..."   # or OPENROUTER_API_KEY
# one-time: ensure file-browser viewer deps are installed
cd $HOME/skills/skills/file-browser && npm install
```

Get a key at <https://openrouter.ai/settings/keys>.

## How it works

1. **Parse args** — description + flags.
2. **Resolve session dir** — `<git-root>/.diagrams/<YYYYMMDD-HHMM>-<slug>/`. Outside a git repo: `~/Documents/llm-diagrams/<cwd>-<slug>/`.
3. **Classify type** — if `--type` not provided, OpenRouter classifies into one of 8 types.
4. **Load refs** — preset style tokens, `references/style-foundations.md`, `references/composition-rules.md`, `references/types/<type>.md`, plus `references/svg-contract.md` for SVG runs.
5. **Refine OR emit** — PNG: refine to image-gen prompt → image API. SVG: LLM emits markup directly.
6. **Save** — scratch mode writes `v1.png` / `v1.svg` + `prompt.md` + `meta.json`; versioned mode also writes `diagram.spec.yaml` + `manifest.json`. Spawn the file-browser gallery.

## Diagram types

| Type | Alias | When prompt mentions… |
| --- | --- | --- |
| `system-architecture` | `arch` | services, components, deployment, infrastructure |
| `data-flow` | `flow` | data flows, transformations, sources/sinks, pipeline |
| `workflow` | `wf`, `process` | steps, approvals, handoffs, swimlanes, business process |
| `sequence` | `seq` | "user does X then Y", interactions over time, API calls |
| `er-diagram` | `er` | entities, tables, relationships, schema |
| `state-machine` | `state` | states, transitions, lifecycle, status |
| `c4-context` | `c4` | system in its environment, external users + systems |
| `c4-container` | — | internal containers (web, api, db, queue) inside a system |

## Flags

| Flag | Default | Notes |
| --- | --- | --- |
| `description` (positional) | — | Free-text. Required unless `--regen`. |
| `--type` | auto-classify | One of the 8 types or an alias. |
| `--preset` | `warm` | Visual style: `warm`, `mono`, `pastel`, `cyberpunk`. See "Style presets" below. |
| `--format` | `png` | `png` or `svg`. |
| `--quality` | `medium` | `low`, `medium`, `high`. PNG only; OpenRouter passes through. |
| `--aspect-ratio` | `16:9` | PNG only. |
| `--regen "<feedback>"` | — | Iterate on the most recent session. Inherits preset/type/format from prior session. |
| `--new` | off | Force a fresh session even when a recent one exists. |
| `--no-open` | off | Skip auto-opening the browser tab. |
| `--slug` | derived | Override the slug in the session dir name. |
| `--versioned` | off | Write git-trackable artifacts under `docs/diagrams/<slug>/` instead of ignored scratch output. |

## Capability Matrix

| Need | Recommended mode | Why |
| --- | --- | --- |
| Architecture or C4 diagrams for PR/RFC review | `--format svg --versioned --engine skeleton` | Stable coordinates, crisp labels, deterministic spec + manifest. |
| Workflow/process maps | `--type workflow --format svg --versioned` | Swimlane/stage-friendly layout with decision and handoff conventions. |
| ERD/database design | `--type er --format svg --versioned` | Entities and relationships stay hand-editable and diffable. |
| Presentation or executive visuals | `--format png --preset pastel` | Higher visual richness; keep as scratch unless the image belongs in docs. |
| Fast iteration on a draft | default scratch output or `--regen` | Avoids polluting docs until the shape stabilizes. |

## Engines

`vd:diagram` is moving toward a two-pass architecture for structurally-rich diagram types: pass-1 LLM emits a YAML skeleton (structure only); Python computes coordinates; pass-2 LLM paints the SVG with positions locked.

`--engine` selects between `free` (pure-LLM SVG path, kept as the escape hatch) and `skeleton` (YAML → layout → paint). SVG defaults to `skeleton` for `system-architecture`, `data-flow`, `workflow`, `c4-context`, `c4-container`, and `er-diagram`; `sequence` and `state-machine` still default to `free`. See `references/skeleton-contract.md` and `references/painter-contract.md` for the contracts.

## Style presets

All presets share the same iconography, line weights, density limits, and label-placement rules. Only the palette and aesthetic feel differ.

| Preset | Surface | Primary | Accent | When to pick it |
| --- | --- | --- | --- | --- |
| `warm` (default) | cream `#faf8f3` | deep slate | warm amber | Pitch decks, design docs, blog hero images, internal architecture write-ups |
| `mono` | white `#ffffff` | near-black | none — uses 3.5px border + `[Subject]` tag for highlight | PR-diffable engineering docs, B&W print, technical specs, RFCs |
| `pastel` | slate-50 `#f8fafc` | slate-800 | sky-600 | PowerPoint, executive presentations, customer-facing docs, marketing |
| `cyberpunk` | near-black `#0a0e1a` | slate-200 | neon cyan + glow | Conference slides, demo videos, dev-tool launch graphics, OG/social |

**Customizing a preset:** edit `references/presets/<name>/style-tokens.md`. Palette + aesthetic + CSS-vars block live there. Iconography and rules live in shared `style-foundations.md` and `composition-rules.md`.

**Adding a new preset:** create `references/presets/<your-name>/style-tokens.md` following the warm template, then add the name to `SUPPORTED_PRESETS` in `scripts/generate.py`. No other code changes needed — type refs are preset-agnostic.

## Output location

- Inside a git repo → `<git-root>/.diagrams/<YYYYMMDD-HHMM>-<slug>/`
- Outside a git repo → `~/Documents/llm-diagrams/<cwd-basename>-<YYYYMMDD-HHMM>-<slug>/`
- With `--versioned` → `<git-root>/docs/diagrams/<slug>/`

Inside a git repo, `<git-root>/.diagrams/.gitignore` is auto-created on first run with:
```
*
!.gitignore
```
That ignores every artifact while keeping the gitignore itself tracked. Your repo's root `.gitignore` is never touched.

Each session dir contains:
- `v1.<png|svg>`, `v2.<png|svg>`, … — the variants
- `prompt.md` — original description, refined prompt, iteration history
- `meta.json` — type, format, models, original description, list of variant filenames
- `diagram.spec.yaml` — versioned mode only; source intent for code review
- `manifest.json` — versioned mode only; latest variant + deterministic metadata

See `references/versioned-artifacts.md` for artifact conventions and review workflow.

## Iteration: `--regen` vs `--new`

- `--regen "<feedback>"` — finds the **most recent** session under the current repo's `.diagrams/`, re-uses its type and format, appends `<feedback>` to the original description, drops `v2.<ext>` (or `v3`, `v4`, …) alongside the original. The positional description is ignored when `--regen` is used.
- `--versioned --regen "<feedback>"` — same iteration behavior, but searches `docs/diagrams/` and updates `diagram.spec.yaml` / `manifest.json` to point at the newest variant.
- `--new` — forces a fresh session dir even if a recent one exists. Requires a positional description.
- Default — creates a new session dir from the current description.

`--regen` reads `meta.json` for type/format/original-description, so SVG sessions regen as SVG and PNG sessions regen as PNG automatically.

## PNG vs SVG

|  | PNG | SVG |
| --- | --- | --- |
| Visual richness | High | Medium |
| Text-label crispness | Variable | Excellent |
| Approx cost / diagram | $0.04–0.19 | $0.005–0.02 |
| Latency | 30–90s | 10–20s |
| Editable | No | Yes (any vector tool) |
| Best for | Pitch decks, design docs | Engineering docs, PR-diffable diagrams |

## Customizing styles

Every diagram inherits from:
- `references/style-tokens.md` — palette, typography, iconography, line weights
- `references/composition-rules.md` — whitespace, hierarchy, label placement, density
- `references/types/<type>.md` — type-specific prompt template + golden examples
- `references/svg-contract.md` — SVG output schema (only loaded when `--format svg`)

Edit these once and every future diagram inherits the change. Keep type refs ≤120 lines — they are prompt fuel, not documentation.

## Limitations

- PNG text labels can render garbled when there are >12 elements with long names. Workarounds: shorten labels, switch to `--format svg`.
- SVG layouts overlap on >20-element diagrams (LLM spatial reasoning weakness). Workaround: split into two diagrams, or use PNG and re-render with a shorter description.
- `--regen` operates on the **latest** session under the current `.diagrams/` dir. Running it from a different repo won't find the original session.

## Dependencies

- Python: `requests` (already in the shared `~/.claude/skills/.venv`)
- Node: the `file-browser` skill (`cd $HOME/skills/skills/file-browser && npm install`) for the gallery viewer
- Env: `OPEN_ROUTER_KEY` or `OPENROUTER_API_KEY`

## Local Verification

```bash
python3 -m py_compile skills/diagram/scripts/generate.py \
  skills/diagram/scripts/skeleton_schema.py \
  skills/diagram/scripts/skeleton_layout.py
PYTHONPATH=skills/diagram/scripts python3 -m unittest discover \
  skills/diagram/scripts/tests
```
