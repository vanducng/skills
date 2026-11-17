# Charts that stay readable on the page

A chart is shown no wider than the page's content area, so its text shrinks by the same factor as the image.

```
rendered text px ≈ font px × min(1, content width / chart width)
```

`chart width` is the chart's own CSS width (the SVG viewBox width), not the PNG's pixel width: a 2x export doubles both, and the ratio is unchanged.

Content width measured on a full-width page (`--content-width max`), body text 16px:

| Browser window | Content width |
|---|---|
| 1600px | about 1235px |
| 1440px | about 1057px |

Aim for 14px or more at 1235px. Solve for the font size to author with:

```
font px ≥ 14 × chart width / 1235
```

| Chart width | Smallest font |
|---|---|
| 1000 | 14 (no shrink) |
| 1400 | 16 |
| 1800 | 21 |
| 2400 | 28 |

A chart that needs 28px labels is too wide: split it or drop categories instead.

## Mermaid

Set the font in the renderer, not by enlarging the PNG: scaling a bitmap grows the chart and its text together, so the ratio above does not move. With the `pele` renderer pass the `fontSize` render option, 18 to 22 for a typical flow or sequence diagram, and re-measure.

## SVG to PNG at 2x

Wrap the SVG in a page sized to its viewBox and screenshot it with headless Chrome at device scale 2. `W` and `H` are the viewBox width and height.

```bash
CHROME=${CHROME:-google-chrome}   # macOS: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
{ printf '<!doctype html><style>html,body{margin:0}svg{display:block;width:%spx;height:%spx}</style>' "$W" "$H"
  cat chart.svg; } > chart.html
"$CHROME" --headless=new --hide-scrollbars --force-device-scale-factor=2 \
  --window-size="$W,$H" --screenshot="$PWD/chart.png" "file://$PWD/chart.html"
```

The PNG is then `2W x 2H`. `to_confluence.py` reads that size from the PNG header for `data-width`/`data-height`; the figure itself is 1800px wide in pixel mode, which the page clamps to its content width.
