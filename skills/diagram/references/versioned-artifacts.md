# Version-Controlled Diagram Artifacts

Use `--versioned` when a diagram should live with the codebase: architecture docs, ADRs, RFCs, ERDs, workflow maps, release notes, and reviewable design proposals.

## Directory Shape

```
docs/diagrams/<slug>/
  diagram.spec.yaml
  manifest.json
  prompt.md
  meta.json
  v1.svg
  v2.svg
```

For PNG renders the variant files are `v1.png`, `v2.png`, and so on. SVG is preferred for architecture, workflow, ERD, and C4 because it is readable in code review and hand-editable.

## Artifact Roles

| File | Role | Review expectation |
| --- | --- | --- |
| `diagram.spec.yaml` | Human intent: type, format, preset, engine, description, latest variant | Read this first in PR review. It should explain why the diagram exists. |
| `manifest.json` | Deterministic machine metadata: latest variant and known variants | Stable diffs; no timestamps. |
| `prompt.md` | Original/refined prompt history | Useful for regeneration and audit trail. |
| `meta.json` | Runtime metadata from the generator | Useful for debugging model/preset choices. |
| `vN.svg` / `vN.png` | Rendered variant | Latest is referenced by `diagram.spec.yaml` and `manifest.json`. |

## Review Workflow

1. Generate with an explicit slug:
   ```bash
   ~/.claude/skills/.venv/bin/python3 $HOME/skills/skills/diagram/scripts/generate.py \
     --type workflow --format svg --versioned --slug checkout-fulfillment \
     "checkout workflow from cart to shipment with payment, fraud review, warehouse pick, and notification"
   ```
2. Commit the full `docs/diagrams/<slug>/` folder.
3. In PR review, inspect `diagram.spec.yaml` first, then view `manifest.json.latest`.
4. For a revised render, rerun the same slug. The generator writes `v2.svg` (or next variant) and updates `latest`.
5. Keep older variants when the history is useful; delete superseded variants when they add noise.

## Modern Diagram Quality Bar

- Prefer SVG for reviewable architecture, workflow, ERD, C4, and state diagrams.
- Use `--engine skeleton` for structured types so coordinates are computed before painting.
- Keep one abstraction level per diagram; split context/container/component views.
- Encode meaning redundantly: color + shape, line style, position, or label.
- Keep active semantic colors low and rely on shape/line semantics for extra dimensions.
- Use stable slugs (`checkout-fulfillment`, `billing-erd`) instead of timestamp names for docs.

## When Not To Use It

- Exploratory prompt iteration where most outputs will be thrown away.
- Presentation-only PNGs that are not part of docs or an ADR.
- Diagrams containing sensitive infrastructure details that should not enter the repo.
