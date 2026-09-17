# Illustrated how-tos (screenshots, callouts, PDF)

Use this for any how-to that points at a UI: HTML, PDF, Markdown, slides, README.
Not PDF-only. Not one admin product.

A marker that sits on the wrong control teaches the wrong click. Wrong overlay
is worse than no overlay.

## Choose a method (first that holds)

1. **Crop + legend.** Frame the control. Numbered list under the figure. No discs.
2. **Stamp live, then capture.** Put a small marker on the real element in the
   page (or native UI), then screenshot. The pixels already contain the number.
3. **Vector overlay in the image's own space.** SVG `viewBox` equals the PNG's
   intrinsic width x height, stretched over the `img`. Coordinates are image
   pixels and scale in print.

Stop at 1 unless the reader would miss the control.

## Stamp live (browser)

Marker is 18px. Sit it on the control, not on a neighbor label. At most three
per shot; crop or split instead of adding more.

```javascript
function stampCallout(el, n) {
  if (!el) throw new Error("callout target missing: " + n);
  const r = el.getBoundingClientRect();
  const m = document.createElement("div");
  m.dataset.callout = String(n);
  Object.assign(m.style, {
    position: "fixed",
    left: Math.max(0, r.left - 20) + "px",
    top: Math.max(0, r.top + r.height / 2 - 9) + "px",
    width: "18px",
    height: "18px",
    borderRadius: "50%",
    background: "#c0392b",
    color: "#fff",
    font: "700 11px/18px sans-serif",
    textAlign: "center",
    zIndex: "2147483647",
    pointerEvents: "none",
  });
  m.textContent = String(n);
  document.body.appendChild(m);
}
stampCallout(document.querySelector("<selector>"), 1);
```

`left`/`top` px here are viewport coordinates at capture time. That is correct.
The ban is px in the **published** HTML on a later resized bitmap.

## SVG overlay (when the PNG already exists)

Intrinsic size of `step.png` must match `viewBox`. CSS makes both `width: 100%`.

```html
<figure>
  <div class="shot">
    <img src="step.png" width="1600" height="900" alt="">
    <svg viewBox="0 0 1600 900" aria-hidden="true">
      <circle cx="140" cy="260" r="9" fill="#c0392b"/>
      <text x="140" y="264" text-anchor="middle" fill="#fff" font-size="11" font-family="sans-serif">1</text>
    </svg>
  </div>
  <figcaption>1. The control the reader should use.</figcaption>
</figure>
```

```css
.shot { position: relative; }
.shot img, .shot svg { display: block; width: 100%; height: auto; }
.shot svg { position: absolute; inset: 0; pointer-events: none; }
```

Read `cx`/`cy` from the PNG (image editor, or measure in a viewer at 100%
zoom). Do not copy coordinates from a chat-scaled preview.

## Marker design

- 16-18px disc, 11-12px type.
- High contrast. No shadow large enough to hide the control.
- On the control, not covering the thing you are naming.
- Caption list still required. The marker is a pointer, not the instruction.

## Verify (must pass before ship)

Visual: open the rendered page or PDF. For each number, say the control it
should mark. Off by more than a few millimeters → delete overlays, keep the
legend.

Mechanical, on published HTML (fail closed):

```bash
# px on overlay markers will miss once the bitmap is scaled
if rg -n 'position:[[:space:]]*absolute[^"]*(left|top):[[:space:]]*[0-9.]+px' guide.html; then
  echo 'fail: overlay uses CSS px; use live-stamp or SVG viewBox' >&2
  exit 1
fi
```

Evidence to keep with the guide:

- Live-stamp PNG, or
- SVG overlay whose viewBox matches the PNG, or
- Legend-only figures

If none of those exist, do not overlay.

## Do not

- Guess `top`/`left` from a scaled screenshot in chat.
- Put CSS px on an `img { max-width: 100% }`.
- Cover the control you are labeling.
- Ship without opening the rendered artifact.
- Stack more than three markers on one figure.
