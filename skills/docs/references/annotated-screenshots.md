# Annotated screenshots (HTML and PDF how-tos)

Use this whenever a how-to, operator guide, or PDF puts numbered markers on a screenshot.

Wrong overlay is worse than no overlay. A number sitting on the wrong control teaches the wrong click.

## Failure that keeps happening

CSS `position: absolute; left: 18px; top: 198px` on a screenshot that later
`max-width: 100%` in HTML/PDF. Coordinates guessed from a chat-scaled image
preview. Result: a 28px disc covering the wrong cell, not the checkbox or Go
button.

## Default: legend only

Numbered list under the figure. No discs on the image.

Overlay only when you can place the marker on the live control, then screenshot,
or when you have percentages of the **rendered** image box and you verified the
PDF.

## How to overlay (only if you must)

1. **Stamp in the browser, then capture.** Inject a small marker next to the
   real DOM node (`getBoundingClientRect` of the checkbox, action select, Go
   button). The PNG already has the number. Do not guess px later.
2. **If you overlay in HTML**, wrap `img` in `.shot { position: relative }` and
   place badges with **percentages of that box**, not px of the original file.
   Image will shrink in print. Px will miss.
3. **Badge size.** 16-18px disc, 11-12px type. No drop shadow big enough to
   hide the control. The marker sits on the control, not on the label of the
   thing next to it.
4. **At most three markers per figure.** More than that, crop or split shots.
5. **Verify.** Open the PDF. For each number, name the control it should mark.
   If it is off by more than a few millimeters, delete the overlays and keep
   the legend.

## Mechanical checks (must pass before ship)

Run these on the HTML (or the HTML that printed the PDF). Fail closed.

```bash
# px overlays on a max-width image will miss in print
if rg -n 'class="badge"[^>]*(left|top)[[:space:]]*:[[:space:]]*[0-9.]+px' guide.html; then
  echo 'fail: guessed px badge placement' >&2
  exit 1
fi
```

Evidence to keep with the guide:

- Live-stamp PNG (markers injected next to real DOM nodes, then captured), or
- Legend-only figures (no discs on the image)

If neither exists, do not overlay. Do not guess.

## Do not

- Guess `top`/`left` from a scaled screenshot in chat.
- Use px against an `img { max-width: 100% }`.
- Cover the control you are labeling.
- Ship the PDF without opening it.

## Caption still required

Even with overlays, keep the numbered list under the figure. The overlay is a
pointer, not the instruction.
