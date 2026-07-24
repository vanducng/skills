---
name: diagram
description: "Generate modern reviewable diagrams (system architecture, workflow, data flow, sequence, ER, state-machine, C4) via OpenRouter image-gen or LLM-emitted SVG. Auto-classifies diagram type from prompt; --type to override. Default scratch output goes to the resolved workbench visuals path; --versioned writes git-trackable specs and variants under docs/diagrams/."
license: MIT
argument-hint: "[description] [--type TYPE] [--preset PRESET] [--format png|svg] [--versioned] [--regen FEEDBACK] [--new]"
metadata:
  author: vanducng
  version: "1.0.1"
---

# vd:diagram

Turn natural-language descriptions into reviewable diagram images and version-controlled diagram artifacts. Two render paths:
- **PNG** (default): generates the image. Default image provider is **codex** (`gpt-image-2` via your ChatGPT subscription - cost-optimized, no per-image API spend), with automatic fallback to OpenRouter `gpt-5.4-image-2` when codex is unavailable and an OpenRouter key is set. Force the API path with `--provider openrouter`. With `--provider codex` and an explicit `--type`, no `OPEN_ROUTER_KEY` / `OPENROUTER_API_KEY` is required.
- **SVG** (`--format svg`): the LLM emits the SVG markup directly. Cheaper, crisper labels, hand-editable.

Use `--versioned` only when the diagram source, variants, and manifest are themselves review artifacts for an ADR/spec/PR. It writes a stable folder under `docs/diagrams/<slug>/` with:
- `diagram.spec.yaml` - reviewable source intent (type, preset, engine, description, latest variant)
- `manifest.json` - deterministic metadata for automation
- `v1.svg`, `v2.svg`, ... or `v1.png`, `v2.png`, ... - rendered variants

For a diagram that merely illustrates a docs page, keep the generation session in the injected `Visuals:` path, copy the final rendered image into the docs' local assets folder (for example `docs/design/assets/<slug>.svg`), and link that one asset from Markdown. Do not create `docs/diagrams/` just because a docs page references an image.

## Quick Start

```bash
# Resolve the Python interpreter: shared venv when present, else plain python3 (`pip install --user requests`)
PY="$([ -x "$HOME/.claude/skills/.venv/bin/python3" ] && echo "$HOME/.claude/skills/.venv/bin/python3" || echo python3)"

# Auto-detect type, default PNG
$PY $HOME/skills/skills/diagram/scripts/generate.py \
  "system architecture for an OAuth signup flow with FastAPI backend"

# Explicit type, SVG output
$PY $HOME/skills/skills/diagram/scripts/generate.py \
  --type sequence --format svg \
  "user logs in: User → App → Auth Provider → callback"

# Version-controlled workflow artifact for docs/diagrams/
$PY $HOME/skills/skills/diagram/scripts/generate.py \
  --type workflow --format svg --versioned --slug checkout-fulfillment \
  "checkout workflow from cart review through payment, fraud check, warehouse pick, and shipment"

# Iterate on the latest diagram with feedback
$PY $HOME/skills/skills/diagram/scripts/generate.py \
  --regen "make the auth box use the warning color"

# Pick a different visual style preset (cyberpunk for talk slides)
$PY $HOME/skills/skills/diagram/scripts/generate.py \
  --preset cyberpunk \
  "data flow: Kafka → Spark → ClickHouse → Grafana"

# Use a clear draft/screenshot as layout guidance for Codex PNG generation
$PY $HOME/skills/skills/diagram/scripts/generate.py \
  --format png --provider codex --reference-image draft.png \
  "polished cloud architecture diagram; follow the reference layout exactly"
```

## Interactive HTML ERD (`er_html.py`)

For database ER diagrams that need to be **explored**, not just viewed, use the deterministic
`er_html.py` generator (no LLM, no API key). It emits **one self-contained HTML file** built on
Cytoscape.js with a fully interactive graph:
- **HTML ER cards** (header band in domain-group colour, `◆` PK / `→` FK glyphs, column types) drawn inside the graph via cytoscape-node-html-label
- **draggable nodes** (edges follow), curved edges, pan/zoom, re-layout
- **single-click** a table → spotlight it + its relationship chain; the **participating FK columns are highlighted inside the cards** (not as text on the lines)
- **click a relationship line** → spotlight just its two joined tables, mark the join columns, and open a relationship summary (cardinality + `ON DELETE` + both columns)
- **selectable highlight depth** (1 / 2 / 3 / All hops; default 1) for the chain
- **hide/show individual entities** (card `×` to hide; sidebar eye or "show N hidden" to restore)
- **find-path** between two tables (shortest FK chain, highlighted with join columns)
- **schema insights** panel (missing PK, FK type mismatch, unindexed FK, orphan tables - click to jump to the table)
- **shareable URL** (filters/selection encoded in the link) + **saved layout** (dragged positions persist per schema in localStorage)
- **group hulls** (colored regions behind domain groups) + a **minimap** (click/drag to navigate)
- **double-click** a table → details drawer (columns, types, PK/FK/audit badges, FK targets + `ON DELETE` rules, incoming references, indexes, row counts)
- **crow's-foot cardinality** at edge ends (`1` / `N`, `1:1` when the FK is unique); edge **colour encodes `ON DELETE`** (CASCADE/SET NULL/NO ACTION)
- **per-entity "show all columns"** expander (header `⊕` or the "+N more" row)
- live search (tables + columns), domain-group filters, show/hide audit columns, show/hide framework tables, columns-on-nodes toggle
- **collapsible left (filters) + right (details) sidebars**
- **keyboard shortcuts** + a `?` help overlay (`/` search, `a`/`t`/`c`/`n` toggles, `[`/`]` panels, `f` fit, `g` re-layout, `+`/`-` zoom, `s` clear, `r` reset, `Esc`)

By default it **inlines** Cytoscape (~450 KB total) so the file works fully offline; pass `--cdn`
for a ~75 KB file that loads Cytoscape from jsdelivr.

```bash
# 1a. introspect a Postgres DB into schema.json (psql; no python DB deps)
psql "$DSN" -t -A -c "$(python3 $HOME/skills/skills/diagram/scripts/er_html.py --print-sql)" > schema.json

# 1b. OR a MySQL DB (8.0+ / MariaDB 10.5+). --raw is REQUIRED (default --batch escaping corrupts JSON);
#     -D selects the DB so DATABASE() resolves; pass the password via MYSQL_PWD, never on the cmdline.
MYSQL_PWD="$DB_PASS" mysql -N --raw -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -D "$DB_NAME" \
  -e "$(python3 $HOME/skills/skills/diagram/scripts/er_html.py --print-sql --dialect mysql)" > schema.json

# 2. (optional) write meta.json - domain groups, classifications, descriptions, framework_tables, audit_columns
#    (add "database_type": "MySQL" so --emit-dbml labels the Project correctly)
#    see the docstring in er_html.py for the shape

# 3. generate the interactive ERD
python3 $HOME/skills/skills/diagram/scripts/er_html.py \
  --schema schema.json --meta meta.json -o erd.html        # self-contained (offline)
  # add --cdn for a ~140 KB file that pulls Mermaid/svg-pan-zoom from jsdelivr
```

### DBML interop (dbdocs.io / dbdiagram.io)

The generator round-trips with **DBML**:

```bash
# export our schema → DBML (no deps) - publish with `dbdocs build`, or paste into dbdiagram.io
er_html.py --schema schema.json --meta meta.json --emit-dbml schema.dbml

# import a .dbml → our schema JSON → interactive HTML (needs @dbml/core: npm i @dbml/core)
node $HOME/skills/skills/diagram/scripts/dbml_to_schema.mjs schema.dbml > schema.json
er_html.py --schema schema.json -o erd.html

# extract a live DB straight to DBML with the official tool (alternative to our --print-sql):
#   npm i -g @dbml/cli && db2dbml postgres '<conn>?schemas=public' -o schema.dbml
```

So: **DB → DBML** via our `--emit-dbml` (from introspected JSON) or `db2dbml`; **DBML → our HTML** via `dbml_to_schema.mjs`. The DBML carries tables, columns (pk/not null), `Ref … [delete: …]`, and domain `TableGroup`s.

Schema JSON is DB-agnostic (any source that emits the documented shape works). `meta.json` is
optional but recommended - it drives the colored domain groups, the write-pattern classification
shown in the docs drawer, and which tables are hidden as "framework" by default. When to use this
vs the image/SVG `er` type: **HTML** for living schema docs you click through and filter; **SVG**
(`--type er --format svg --versioned`) for a static, diffable diagram in a PR/RFC.

## Setup

```bash
export OPEN_ROUTER_KEY="sk-or-v1-..."   # or OPENROUTER_API_KEY; required for SVG, auto-type classification, or --provider openrouter
# one-time: ensure file-browser viewer deps are installed
cd $HOME/skills/skills/file-browser && npm install
```

Get an OpenRouter key at <https://openrouter.ai/settings/keys>. Codex PNG generation uses the Codex CLI ChatGPT login instead.

## How it works

1. **Parse args** - description + flags.
2. **Resolve session dir** - `VD_VISUALS_PATH` when set, else the current repo's resolved workbench visuals path, else `<git-root>/.diagrams/<YYYYMMDD-HHMM>-<slug>/`. Outside a git repo: `~/Documents/llm-diagrams/<cwd>-<slug>/`.
3. **Classify type** - if `--type` not provided, OpenRouter classifies into one of 8 types.
4. **Load refs** - preset style tokens, `references/style-foundations.md`, `references/composition-rules.md`, `references/types/<type>.md`, plus `references/svg-contract.md` for SVG runs.
5. **Prompt OR emit** - PNG: build a Codex prompt locally, or refine through OpenRouter when using `--provider openrouter`. SVG: LLM emits markup directly.
6. **Save** - scratch mode writes `v1.png` / `v1.svg` + `prompt.md` + `meta.json`; versioned mode also writes `diagram.spec.yaml` + `manifest.json`. Spawn the file-browser gallery.

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
| `c4-container` | - | internal containers (web, api, db, queue) inside a system |

## Flags

| Flag | Default | Notes |
| --- | --- | --- |
| `description` (positional) | - | Free-text. Required unless `--regen`. |
| `--type` | auto-classify | One of the 8 types or an alias. |
| `--preset` | `warm` | Visual style: `warm`, `mono`, `pastel`, `cyberpunk`. See "Style presets" below. |
| `--format` | `png` | `png` or `svg`. |
| `--provider` | `codex` | PNG image backend. `codex`: `gpt-image-2` via ChatGPT subscription - cost-optimized, OpenRouter fallback. `openrouter`: `gpt-5.4-image-2` via API. |
| `--quality` | `medium` | `low`, `medium`, `high`. PNG only; OpenRouter passes through. |
| `--aspect-ratio` | `16:9` | PNG only. |
| `--reference-image` | none | Attach a draft/screenshot to Codex PNG generation; repeat for multiple images. Ignored by SVG and OpenRouter fallback. |
| `--regen "<feedback>"` | - | Iterate on the most recent session. Inherits preset/type/format from prior session. |
| `--new` | off | Force a fresh session even when a recent one exists. |
| `--no-open` | off | Skip auto-opening the browser tab. |
| `--slug` | derived | Override the slug in the session dir name. |
| `--versioned` | off | Write git-trackable artifacts under `docs/diagrams/<slug>/` instead of ignored scratch output. |

## Capability Matrix

| Need | Recommended mode | Why |
| --- | --- | --- |
| Architecture or C4 diagrams for PR/RFC review | `--format png --provider codex --reference-image draft.png` | Use a simple draft to lock layout, then let gpt-image-2 render a cleaner cloud diagram. |
| Diffable architecture specs | `--format svg --versioned --engine skeleton` | Stable coordinates, crisp labels, deterministic spec + manifest. |
| Workflow/process maps | `--type workflow --format svg --versioned` | Swimlane/stage-friendly layout with decision and handoff conventions. |
| ERD/database design (static, diffable) | `--type er --format svg --versioned` | Entities and relationships stay hand-editable and diffable. |
| Explorable/living DB docs (filter, search, per-table docs) | `er_html.py --schema … --meta …` | Self-contained interactive HTML ERD; no LLM/API key. |
| Explanatory image embedded in docs | scratch output, then copy final asset to `docs/**/assets/` | Keeps specs/manifests out of project docs when only the image matters. |
| Presentation or executive visuals | `--format png --preset pastel` | Higher visual richness; keep as scratch unless the image belongs in docs. |
| Fast iteration on a draft | default scratch output or `--regen` | Avoids polluting docs until the shape stabilizes. |

## Engines

`vd:diagram` is moving toward a two-pass architecture for structurally-rich diagram types: pass-1 LLM emits a YAML skeleton (structure only); Python computes coordinates; pass-2 LLM paints the SVG with positions locked.

`--engine` selects between `free` (pure-LLM SVG path, kept as the escape hatch) and `skeleton` (YAML → layout → paint). SVG defaults to `skeleton` for `system-architecture`, `data-flow`, `workflow`, `c4-context`, `c4-container`, and `er-diagram`; `sequence` and `state-machine` still default to `free`. See `references/skeleton-contract.md` and `references/painter-contract.md` for the contracts.

Workflow skeleton layouts use horizontal swimlane rows: groups become ownership lanes top-to-bottom, and steps flow left-to-right inside each row. Other skeleton types keep the group-column layout.

## Style presets

All presets share the same iconography, line weights, density limits, and label-placement rules. Only the palette and aesthetic feel differ.

| Preset | Surface | Primary | Accent | When to pick it |
| --- | --- | --- | --- | --- |
| `warm` (default) | cream `#faf8f3` | deep slate | warm amber | Pitch decks, design docs, blog hero images, internal architecture write-ups |
| `mono` | white `#ffffff` | near-black | none - uses 3.5px border + `[Subject]` tag for highlight | PR-diffable engineering docs, B&W print, technical specs, RFCs |
| `pastel` | slate-50 `#f8fafc` | slate-800 | sky-600 | PowerPoint, executive presentations, customer-facing docs, marketing |
| `cyberpunk` | near-black `#0a0e1a` | slate-200 | neon cyan + glow | Conference slides, demo videos, dev-tool launch graphics, OG/social |

**Customizing a preset:** edit `references/presets/<name>/style-tokens.md`. Palette + aesthetic + CSS-vars block live there. Iconography and rules live in shared `style-foundations.md` and `composition-rules.md`.

**Adding a new preset:** create `references/presets/<your-name>/style-tokens.md` following the warm template, then add the name to `SUPPORTED_PRESETS` in `scripts/generate.py`. No other code changes needed - type refs are preset-agnostic.

## Output location

Scratch (non-versioned) output: write to `VD_VISUALS_PATH` when set; otherwise use the repo workbench resolver. In feature-first repos this is usually the injected `Visuals:` path, falling back to the global scratch visuals path when there is no feature signal. Each session gets a `<YYYYMMDD-HHMM>-<slug>/` subdir. Treat this as the home for brainstorming, reports, and review iterations; promote only the final rendered image to a docs assets folder when a docs page needs a visual.

- Outside a git repo → `~/Documents/llm-diagrams/<cwd-basename>-<YYYYMMDD-HHMM>-<slug>/`
- With `--versioned` → `<git-root>/docs/diagrams/<slug>/` (always; versioned diagrams stay in `docs/`)

Inside a git repo, scratch output is auto-ignored by the `.gitignore` managed in the resolved visuals/session parent. Your repo's root `.gitignore` is never touched.

Each session dir contains:
- `v1.<png|svg>`, `v2.<png|svg>`, … - the variants
- `prompt.md` - original description, refined prompt, iteration history
- `meta.json` - type, format, models, original description, list of variant filenames
- `diagram.spec.yaml` - versioned mode only; source intent for code review
- `manifest.json` - versioned mode only; latest variant + deterministic metadata

See `references/versioned-artifacts.md` for artifact conventions and review workflow.

## Final output handoff

When reporting a finished diagram, give the user an openable location, not just `v1.svg` or a session folder name:
- Primary rendered file as a clickable absolute file link: `[v2.svg](/absolute/path/to/v2.svg)`
- Plain browser URI when useful: `file:///absolute/path/to/v2.svg`
- Session directory path, so they can find `prompt.md`, `meta.json`, and prior variants
- For `--versioned`, include `diagram.spec.yaml` and `manifest.json` alongside the rendered file
- If the gallery starts, include the gallery URL too, but do not use it as the only location

Repo-relative paths are fine as secondary context, but the final handoff must include either an absolute path/link or a `file://` URI for every finalized output artifact.

## Iteration: `--regen` vs `--new`

- `--regen "<feedback>"` - finds the **most recent** session under the current resolved scratch parent, re-uses its type and format, appends `<feedback>` to the original description, drops `v2.<ext>` (or `v3`, `v4`, …) alongside the original. The positional description is ignored when `--regen` is used.
- `--versioned --regen "<feedback>"` - same iteration behavior, but searches `docs/diagrams/` and updates `diagram.spec.yaml` / `manifest.json` to point at the newest variant.
- `--new` - forces a fresh session dir even if a recent one exists. Requires a positional description.
- Default - creates a new session dir from the current description.

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
- `references/style-foundations.md` - palette, typography, iconography, line weights (per-preset palette overrides in `references/presets/<name>/style-tokens.md`)
- `references/composition-rules.md` - whitespace, hierarchy, label placement, density
- `references/types/<type>.md` - type-specific prompt template + golden examples
- `references/svg-contract.md` - SVG output schema (only loaded when `--format svg`)

Edit these once and every future diagram inherits the change. Keep type refs ≤120 lines - they are prompt fuel, not documentation.

## Limitations

- PNG text labels can render garbled when there are >12 elements with long names. Workarounds: shorten labels, switch to `--format svg`.
- SVG layouts overlap on >20-element diagrams (LLM spatial reasoning weakness). Workaround: split into two diagrams, or use PNG and re-render with a shorter description.
- `--provider codex` is not fully keyless in the current CLI: startup still fails without `OPEN_ROUTER_KEY` / `OPENROUTER_API_KEY` before the Codex provider branch runs.
- `--regen` operates on the **latest** session under the current `.diagrams/` dir. Running it from a different repo won't find the original session.

## Dependencies

- Python: `requests` (in the shared `~/.claude/skills/.venv` when present; otherwise `pip install --user requests`)
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
