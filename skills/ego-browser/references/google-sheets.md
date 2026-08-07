# Google Sheets: reliable cell writes

Sheets is a canvas app: the grid is not DOM. Only two DOM anchors matter, and
the biggest trap is that **cell edits can be silently discarded** - typed text
appears in the editor, no error is shown, "Saving..." never fires, and the value
is gone. Every write must be verified against an independent read.

## Page structure

- Name box (cell reference jump): `input#t-name-box` - a real `<input>`
- Formula bar / cell editor: `#t-formula-bar-input`; when focused the active
  element is a `div.cell-input` (`waffle-rich-text-editor`)
- Sheet tabs: `.docs-sheet-tab`, active tab carries `docs-sheet-active-tab`
- On load a "You're currently signed in as ..." popup may overlay the grid -
  dismiss (click its OK button) before interacting

## Navigating to a cell

Type the reference into the name box and press Enter:

1. focus + clear `#t-name-box`, type `B13`, Enter
2. confirm by reading the name box value back (it may echo extra characters -
   check with `startsWith`, not equality)
3. blur the name box before any grid keystrokes, or typing routes into it

## Writing a cell - what actually commits

**Reliable: synthetic paste event, dispatched in page context.** No OS
clipboard involved. Select the target cell first, then:

```js
const dt = new DataTransfer()
dt.setData('text/plain', value)          // '\t' between cells, one paste fills a row
;(document.activeElement || document.body)
  .dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }))
```

Sheets accepts the untrusted event and commits immediately. TSV in
`text/plain` fills a contiguous row from the anchor cell - prefer one paste
per row over per-cell writes.

**Unreliable - all observed to silently discard the commit** (text lands in
the editor, then vanishes on commit):

- typing into the formula bar or inline editor via `insertText`, then Enter
- per-character CDP key events, then Enter (real CDP Enter included)
- committing by clicking another cell instead of Enter
- OS-clipboard paste (`pbcopy` + CDP `commands:['paste']`) - worked in one
  session phase, silently stopped in the next; do not depend on it

**Danger:** `Delete` on a selected cell *always* commits. A clear-then-retype
sequence whose retype is discarded net-wipes the cell.

## Verifying a write - only one trustworthy read

Fetch a fresh CSV export with a cache-busting query param:

```
https://docs.google.com/spreadsheets/d/<ID>/export?format=csv&gid=<gid>&cb=<nonce>
```

Do NOT trust:

- the formula bar after writing - it shows typed-but-uncommitted text
  (classic false positive: "verified" cells that are actually empty)
- the `gviz/tq?tqx=out:csv` endpoint - caches results for minutes
- absence of an error - discarded commits produce none

The export endpoint rate-limits (HTTP 429) under repeated polling; space out
verification reads.

## Sheet tabs

Click by coordinates from `.docs-sheet-tab` bounding rects, then confirm the
target tab's class contains `docs-sheet-active-tab`. The right-most tab can
sit partially behind the tab-scroll arrows - click its left portion.
