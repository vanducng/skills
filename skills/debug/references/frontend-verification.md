# Frontend Verification

Visual verification of frontend changes via Chrome MCP (Claude Chrome Extension) or the `vd:browser` / `vd:web-e2e` stack as fallback.

## Applicability check

**Skip entirely if the task is not frontend.** Indicators:

- Files modified: `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.html`, `*.css`, `*.scss`, `*.astro`
- Changes touch: components, layouts, pages, styles, DOM structure, UI behavior
- Keywords: render, display, layout, responsive, animation, visual, UI, UX

If none match, skip this technique.

## Step 1 - detect Chrome MCP

Check via `ListMcpResourcesTool` for tools prefixed `chrome__` (e.g. `chrome__navigate`, `chrome__screenshot`).

- **Available** → Step 2A (Chrome MCP)
- **Not available** → Step 2B (`vd:browser` fallback)

## Step 2A - Chrome MCP available

Ensure dev server is running, then:

```
1. chrome__navigate     → http://localhost:3000 (or project dev URL)
2. chrome__screenshot   → capture current page
3. Read the screenshot with the Read tool to inspect visually
```

### Visual checklist

1. **Layout** - positioning correct, no overflow / overlap / clipping
2. **Content** - text, images, data render as expected
3. **Responsive** - resize viewport (if MCP supports) - typical breakpoints: 375 / 768 / 1280
4. **Interactions** - `chrome__click` / `chrome__type` to test interactive elements
5. **Console errors** - `chrome__evaluate` to dump errors

```
chrome__evaluate → "JSON.stringify(window.__consoleErrors || [])"
```

Or rely on Chrome MCP error reporting from tool responses.

### Get rendered content

```
chrome__get_content → DOM/text dump to verify rendered output matches expectations
```

## Step 2B - Chrome MCP not available

Fall back to the `vd:browser` stack (`browse` CLI; against an authed app, attach to a `vd:browser-profile` profile first - see `vd:web-e2e`):

```bash
browse open http://localhost:3000 --local
browse screenshot -o ./verification-screenshot.png
browse snapshot                       # rendered structure
browse eval "JSON.stringify(window.__consoleErrors || [])"
browse stop
```

For console/network evidence over a whole session, capture with `vd:browser-trace` instead of polling.

If `browse` is also unavailable (`npm install -g @browserbasehq/browse-cli`), **skip visual verification** and note in the report:

> Visual verification skipped - no Chrome MCP or browse CLI available.

## Step 3 - analyze

1. **Read the screenshot** - use the Read tool on the PNG
2. **Check console output** - zero errors = pass; any error = investigate before claiming done
3. **Compare with expected** - match against design / user description
4. **Document** - include screenshot path and any issues in the verification report

## Integration with the verification protocol

Frontend verification extends `verification.md`. Final gate after standard checks:

```
Tests pass → Build succeeds → Frontend visual verification → Claim complete
```

Report block:

```
## Frontend verification
- Method:        [Chrome MCP | browse | skipped]
- Screenshot:    ./verification-screenshot.png
- Console errors: [none | <list>]
- Visual check:  [pass | issues found]
- Responsive:    [checked at 375/768/1280 | skipped]
```
