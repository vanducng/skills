# GitHub README hero banner

A repo hero banner is a **brand-locked, fixed-size image** referenced from `README.md`
(`<img src="docs/.../banner.png" width="840">`). The upstream catalog has **no banner
template** - `opendesign search "banner"` returns social-card skills whose styling
would override the repo's brand. So do **not** force a catalog template here. Instead:
evolve a self-contained `banner.html` in the repo's own brand and render it to PNG.

## Pipeline

```
banner.html  →  headless Chrome screenshot @2x  →  banner.png  →  referenced in README
```

1. **Find the brand.** Reuse the repo's existing banner/logo, docs theme tokens
   (`docs/.../theme.css`, an Astro/Starlight config), or the README accent colors.
   If a `banner.html` already exists, **evolve it** - don't restyle from scratch.
2. **Author one self-contained HTML file** at a fixed pixel size. System/`-apple-system`
   font stack only (no web-font fetch). A single `.banner` div of `width × height`,
   `overflow: hidden`, brand background, optional grid + corner glows.
3. **Render at 2× (retina)** with headless Chrome:

   ```bash
   CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"  # or `chromium`
   "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
     --force-device-scale-factor=2 --window-size=1280,300 \
     --screenshot="docs/.../banner.png" "file://$PWD/docs/.../banner.html"
   ```

   `--window-size=W,H` must match the `.banner` size. Output PNG = `2W × 2H`. The
   README usually displays it at `width="840"`, so design for legibility at ~840px wide.

## Sizing

- Width **1280** is a safe default. Height = **just enough for the content** (≈ 260–320).
- Aim for a wide aspect (~**4:1**); a tall banner forces a dead band (see pitfalls).
- The README scales by `width=`, so absolute height only sets the aspect ratio.

## Layout pitfalls (these cause the classic "black gap")

- **Dead bottom band.** A fixed height with `justify-content: center` leaves *symmetric*
  margins, but ambient texture (grid/glow) usually concentrates top-left, so the bottom
  margin reads as a dead black void. Fixes, in order: (a) tighten the height so margins
  are small; (b) extend the grid `mask-image` radius / move its center toward the middle
  so the lower area keeps faint texture; (c) nudge a corner glow toward the bottom.
- **Invisible dim text.** Footer text in a near-bg color (e.g. `#62666d` on `#08090a`)
  renders as black → looks like a gap. Use a readable tone, or drop it.
- **Redundancy.** Don't repeat what the README already shows (tagline, project URL,
  "managed with X" - those live in the README subtitle + badges right below the image).
  A banner that duplicates them just adds height that becomes dead space.

## Verify after generating (MANDATORY)

Never claim done from the HTML alone - **always render, then check the PNG**:

1. **View** the rendered `banner.png` (read it as an image).
2. **Measure** the content bounding box to confirm margins are tight and balanced:

   ```python
   from PIL import Image
   im = Image.open("docs/.../banner.png").convert("RGB"); W,H = im.size; px = im.load()
   # bottom margin is glow-free, so it's the reliable signal:
   def has_content(y, thr=55):
       return any(px[x,y][0]>thr or px[x,y][1]>thr or px[x,y][2]>thr+10 for x in range(0,W,3))
   bot = max(y for y in range(H) if has_content(y))
   print(f"bottom margin = {H-1-bot}px ({(H-1-bot)//2}px @1x)")  # want it small (~20–40 @1x)
   ```

   (The top-left glow makes top-margin detection unreliable; trust the bottom number,
   or measure the box's own border.)
3. **Iterate** height / mask / spacing until the bottom margin is small and the banner
   reads as intentional. Only then update the README and ship.

## Checklist

- [ ] Self-contained HTML, fixed size, system fonts, brand tokens.
- [ ] Rendered @2× via headless Chrome; PNG dimensions = 2× the HTML size.
- [ ] No dead black band; margins small and balanced (verified by measure + view).
- [ ] No content that duplicates the README subtitle/badges.
- [ ] README `<img>` points at the PNG; displays well at its `width=`.
