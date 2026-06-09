# Poster Prompt Engineering

How the poster generator assembles prompts and how to tune them for specific image models.

## Anatomy of a Prompt

Every generated prompt has 5 blocks:

1. **Aspect declaration** — `--aspect a2|a3|square|landscape`
2. **STYLE (locked)** — name, category, description, mood, era, hints
3. **PALETTE (locked)** — name, hex colors, contrast, mood
4. **TEXTURE/MATERIAL (locked)** — material, finish, effect, rendering hints
5. **COMPOSITION (varied)** — grid, whitespace, hierarchy order, focal anchor, secondary positions, shape set, density, rotation jitter
6. **COPY SLOTS** — headline (derived from topic), sub, meta
7. **CONSTRAINTS** — explicit "lock these / vary only these" instructions

The locked vs varied split is the whole point: locked axes preserve style identity, varied axes guarantee per-call variety.

## Axis Lock Semantics

`--lock-axis style,texture` (CLI flag) is for series generation. When passed, you can call `generate.py` repeatedly with different `--seed` values and the locked axes stay fixed while the unlocked axes randomize.

Use cases:
- **Brand series**: lock `style,palette,texture` → vary only layout. All 5 posters feel like one campaign.
- **Texture study**: lock `texture` only → explore many styles with the same material.
- **Free exploration**: lock nothing.

## Variation Pools

The Shape Pool per style is aggregated from all member-image `shape_primitives` during clustering. Each style has 4-8 primitives. Per call, 2-4 are sampled. Five calls × 4 shapes from a pool of 6 = `C(6,4) = 15` distinct subsets — enough to keep a 5-poster series visually distinct.

Position randomization draws from a 9-cell grid (3×3). Density picks from `sparse|medium|dense`. Rotation jitter from `[-8°, +8°]`. Combined entropy: 9 × 3 × 17 × shape_set_combos × hierarchy_perms = thousands of distinct compositions per locked style.

## Model-Specific Tweaks

### Gemini Nano Banana 2 (gemini-3.1-flash-image-preview)

- Reads structured prompts well. The block format above maps cleanly.
- Strong texture/material fidelity — locked TEXTURE block holds.
- Recommend passing prompt as-is.

### GPT Image / GPT-5 Image

- Prefers natural-language prose over bullet structure. Consider piping through a paraphrase step if results feel literal.
- Less reliable at preserving exact hex colors. Pre-load palette as `using a palette dominated by {hex1} and {hex2}` in the headline of the COPY block.

### Imagen / Midjourney

- Imagen: works well with the structured format.
- Midjourney: shorten prompt; emphasize style + texture; rely on `--ar` flag from aspect mapping instead of millimeter dimensions.

## Determinism

`--seed N` makes prompt assembly deterministic — same seed produces same prompt. The image model itself may still introduce sampling variance unless you pass a model-side seed.

## Failure Modes & Fixes

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Outputs in a series look near-identical | Shape Pool too thin for that style | Re-run `cluster.py` after adding more reference images, or widen variation by sampling more shapes |
| Style drifts between calls in a series | Style description too generic | Curate the Style Name + Description rows manually in `poster-styles.csv` |
| Texture not preserved | Model ignored TEXTURE block | Repeat texture material/finish in COPY block or pre-pend to the prompt |
| Color palette ignored | Model deprioritized hex codes | Convert hex to named colors in palette CSV (e.g. "deep navy #0a1f4a") |

## Editing CSVs Manually

The CSVs are the source of truth at runtime. After `cluster.py` produces drafts, you can hand-edit any cell to refine. The audit trail (`data/poster/analysis/clusters.json`) shows which source images map to which cluster — useful when refining style descriptions.

Keep cell values comma-safe (CSV-escape if needed). Re-running `cluster.py` overwrites edits unless you guard your edits in a separate branch / commit.
