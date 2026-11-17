# Check the live page

twg reports success when the body is stored, not when it renders the way you meant. Open the page in a browser at a 1600px wide window (the vd:agent-browser driver works), wait for the images to load, and run this in the page:

```js
(() => {
  const wide = (el) => Math.round(el.getBoundingClientRect().width);
  const content = Math.max(...[...document.querySelectorAll("p")].map(wide));
  const images = [...document.querySelectorAll("img")]
    .filter((img) => img.naturalWidth >= 600)
    .map((img) => ({ alt: img.alt, rendered: wide(img), natural: img.naturalWidth,
                     textScale: +(wide(img) / (img.naturalWidth / 2)).toFixed(2) }));
  const tables = [...document.querySelectorAll("table")].map((t) =>
    [...(t.rows[0]?.cells ?? [])].map((c) => [c.innerText.trim(), wide(c)]));
  return JSON.stringify({ window: innerWidth, content, images, tables }, null, 1);
})()
```

Pass when:

- `content` is about 1235 at a 1600px window. Much less means the page is not full width: update with `--content-width max`.
- Every chart's `rendered` is close to `content` (or to `natural / 2` for a small chart). About 680 means a percentage figure width: rebuild with `to_confluence.py`, which writes pixel widths.
- `textScale` times the chart's font size is 14 or more (`textScale` assumes a 2x export). See `charts.md`.
- Each table's header widths follow the width map in proportion. Equal widths mean the cells lost `data-colwidth`.
- An image that shows the old picture means the body still points at the previous `fileId`.

Report the numbers you measured, not that the update command exited 0.
