# Browser Automation CLI Reference

Technical reference for the `browse` CLI tool (`@browserbasehq/browse-cli`), validated against 0.6.0 and used here for Browserbase remote sessions. The bare `browse` package on npm is a different CLI.

## Table of Contents

- [Architecture](#architecture)
- [Command Reference](#command-reference)
  - [Navigation](#navigation)
  - [Page State](#page-state)
  - [Interaction](#interaction)
  - [Session Management](#session-management)
  - [JavaScript Evaluation](#javascript-evaluation)
  - [Viewport](#viewport)
  - [Network Capture](#network-capture)
  - [CDP Streaming](#cdp-streaming)
- [Configuration](#configuration)
  - [Remote Session Flags](#remote-session-flags)
  - [Environment Variables](#environment-variables)
- [Error Messages](#error-messages)

## Architecture

The browse CLI is a **daemon-based** command-line tool:

- **Daemon process**: A background process manages the browser instance. Auto-starts on the first command (e.g., `browse open`), persists across commands, and stops with `browse stop`.
- **Environment selection**: `browse env` shows the current environment; `browse env remote` switches to Browserbase (requires `BROWSERBASE_API_KEY`), `browse env local` to an isolated local browser. With the API key set, remote is the default desired mode. There is no per-command `--remote` flag in 0.6.x.
- **Attaching to existing targets**: `browse --connect <session-id>` connects the daemon to an existing Browserbase session by ID; `browse --ws <url|port>` points commands at a specific CDP WebSocket URL or port, bypassing the daemon's managed target.
- **Accessibility-first**: Use `browse snapshot` to get the page's accessibility tree with element refs, then interact using those refs.

Local browser driving is out of scope for this skill - use the `agent-browser` skill for local Chrome.

## Command Reference

### Navigation

#### `open <url>`

Navigate to a URL. Auto-starts the daemon if not running.

```bash
browse open https://example.com
browse open https://example.com --wait networkidle   # wait for all network requests to finish (useful for SPAs)
browse open https://example.com --wait domcontentloaded
browse open https://example.com --timeout 60000      # navigation timeout in ms (default 30000)
```

The `--wait` flag controls when navigation is considered complete. Values: `load` (default), `domcontentloaded`, `networkidle`. Use `networkidle` for JavaScript-heavy pages that fetch data after initial load.

##### Context persistence (remote mode only)

```bash
browse open https://app.example.com/login --context-id ctx_abc123 --persist
# ...log in inside the session...
browse stop                              # state saves back to ctx_abc123
```

- `--context-id <id>` - Browserbase context ID whose saved browser state (cookies, storage) the session loads at start.
- `--persist` - save cookies/storage changes back to the context when the session ends. Requires `--context-id`.

Later sessions with the same `--context-id` start already authenticated; omit `--persist` when you don't want further changes written back.

#### `reload`

Reload the current page.

```bash
browse reload
```

#### `back` / `forward`

Navigate browser history.

```bash
browse back
browse forward
```

---

### Page State

#### `snapshot`

Get the accessibility tree with interactive element refs. This is the primary way to understand page structure.

```bash
browse snapshot
browse snapshot --compact                # tree only, no xpath map
```

Returns a text representation of the page with refs like `@0-5` that can be passed to `click`. Use `--compact` for shorter output when you only need the tree.

#### `screenshot [path]`

Take a visual screenshot. Slower than snapshot and uses vision tokens. The path is **positional**.

```bash
browse screenshot ./capture.png          # custom path
browse screenshot ./page.png --full-page # capture entire scrollable page
browse screenshot ./img.jpg --type jpeg --quality 80
```

Other options: `--clip <json>` (region), `--no-animations`, `--hide-caret`.

#### `get <property> [selector]`

Get page properties. Available properties: `url`, `title`, `text`, `html`, `markdown`, `value`, `box`, `visible`, `checked`.

```bash
browse get url                           # current URL
browse get title                         # page title
browse get markdown                      # page content rendered as markdown
browse get text "body"                   # all visible text (selector required)
browse get text ".product-info"          # text within a CSS selector
browse get html "#main"                  # inner HTML of an element
browse get value "#email-input"          # value of a form field
browse get box "#header"                 # bounding box (centroid coordinates)
browse get visible ".modal"              # check if element is visible
browse get checked "#agree"              # check if checkbox/radio is checked
```

**Note**: `get text` requires a CSS selector argument - use `"body"` for full page text.

#### `refs`

Show the cached ref map from the last `browse snapshot`. Useful for looking up element refs without re-running a full snapshot.

```bash
browse refs
```

---

### Interaction

#### `click <ref>`

Click an element by its ref from `browse snapshot` output, or by CSS/XPath selector.

```bash
browse click @0-5                        # click element with ref 0-5
browse click "#submit"                   # click by CSS selector
```

Options: `-b, --button <left|right|middle>`, `-c, --count <n>` (double-click with 2), `-f, --force` (synthetic click when the element has no layout).

#### `click_xy <x> <y>`

Click at exact viewport coordinates.

```bash
browse click_xy 500 300
```

#### `hover <x> <y>`

Hover at viewport coordinates.

```bash
browse hover 500 300
```

#### `type <text>`

Type text into the currently focused element.

```bash
browse type "Hello, world!"
browse type "slow typing" --delay 100    # 100ms between keystrokes
browse type "human-like" --mistakes      # simulate human typing with typos
```

#### `fill <selector> <value>`

Fill an input element matching a CSS selector. **Presses Enter after filling by default.**

```bash
browse fill "#search" "browser automation"          # fill and press Enter (submits)
browse fill "input[name=email]" "user@example.com" --no-press-enter   # fill only
```

Pass `--no-press-enter` on any field where an implicit submit would be wrong.

#### `select <selector> <values...>`

Select option(s) from a dropdown.

```bash
browse select "#country" "United States"
browse select "#tags" "javascript" "typescript"    # multi-select
```

#### `upload <selector> <files...>`

Upload file(s) to an `<input type="file">` element.

```bash
browse upload "#file-input" ./report.pdf
```

#### `press <key>`

Press a keyboard key or key combination.

```bash
browse press Enter
browse press Tab
browse press Escape
browse press Cmd+A                       # select all (Mac)
browse press Ctrl+C                      # copy (Linux/Windows)
```

#### `scroll <x> <y> <deltaX> <deltaY>`

Scroll at a given position by a given amount.

```bash
browse scroll 500 300 0 -300             # scroll up at (500, 300)
browse scroll 500 300 0 500              # scroll down
```

#### `drag <fromX> <fromY> <toX> <toY>`

Drag from one viewport coordinate to another.

```bash
browse drag 80 80 310 100                # drag with default 10 steps
browse drag 80 80 310 100 --steps 20     # more intermediate steps
browse drag 80 80 310 100 --delay 50     # 50ms between steps
browse drag 80 80 310 100 --button right # use right mouse button
```

#### `highlight <selector>`

Highlight an element on the page for visual debugging.

```bash
browse highlight "#submit-btn"           # highlight for 2 seconds (default)
browse highlight ".nav" --duration 5000  # highlight for 5 seconds
```

#### `is <check> <selector>`

Check element state. Available checks: `visible`, `checked`.

```bash
browse is visible ".modal"               # returns { visible: true/false }
browse is checked "#agree"               # returns { checked: true/false }
```

#### `wait <type> [arg]`

Wait for a condition. Types: `load`, `selector`, `timeout`.

```bash
browse wait load                         # wait for page load
browse wait selector ".results"          # wait for element to appear
browse wait timeout 3000                 # wait 3 seconds
```

Options: `-t, --timeout <ms>` (default 30000), `-s, --state <visible|hidden|attached|detached>` for selector waits (default `visible`).

---

### Session Management

#### `start`

Start the browser daemon manually. Usually not needed - the daemon auto-starts on first command.

```bash
browse start
```

#### `stop`

Stop the browser daemon and close the browser.

```bash
browse stop
browse stop --force                      # force kill if daemon is unresponsive
```

#### `status`

Check whether the daemon is running, its connection details, and current environment. `browse status --json` includes the live session's `wsUrl` (a signed Browserbase connect URL when in remote mode).

```bash
browse status
browse status --json
```

#### `env [target]`

Show or switch the browser environment.

```bash
browse env                               # show current environment
browse env remote                        # use Browserbase (requires BROWSERBASE_API_KEY)
browse env local                         # clean isolated local browser (default)
browse env local --auto-connect          # auto-discover the user's local Chrome
browse env local <port|url>              # attach to a specific CDP target
```

#### `pages` / `newpage` / `switch` / `close`

Tab management.

```bash
browse pages                             # list open tabs (index, url, targetId)
browse newpage                           # open a blank tab
browse newpage https://example.com       # open a tab with a URL
browse switch 1                          # switch to tab by index
browse close                             # close the last tab
browse close 2                           # close tab at index 2
```

---

### JavaScript Evaluation

#### `eval <expression>`

Evaluate JavaScript in the page context.

```bash
browse eval "document.title"
browse eval "document.querySelectorAll('a').length"
```

---

### Viewport

#### `viewport <width> <height>`

Set the browser viewport size.

```bash
browse viewport 1920 1080
```

---

### Network Capture

Capture network requests to the filesystem for inspection.

```bash
browse network on                        # enable capture (creates a temp dir of request/response JSON files)
browse network path                      # show the capture directory path
browse network clear                     # clear captured requests
browse network off                       # disable capture
```

This is the driver-side way to capture response **bodies** - the passive CDP firehose (see below) records request metadata only.

---

### CDP Streaming

#### `cdp <url|port>`

Attach a read-only CDP client and stream DevTools protocol events as NDJSON (or `--pretty` for human-readable lines). Accepts a WebSocket URL or a bare port. Against a Browserbase session, pass the `wsUrl` from `browse status --json` - and use it immediately, the signed URL goes stale.

```bash
browse cdp 9222 --pretty                 # watch a local debug port live
browse cdp "$(browse status --json | jq -r .wsUrl)" --pretty   # watch the remote session
browse cdp 9222 --domain Network,Page    # limit domains (default: Network,Console,Runtime,Log,Page)
```

For full trace capture (screenshots, DOM dumps, per-page bisected buckets) on a local Chrome, use the `browser-trace` skill.

---

## Configuration

### Remote Session Flags

These global flags configure a Browserbase session (remote mode only). They go on the command line around the subcommand:

```bash
browse --proxies --region eu-central-1 open https://example.com
```

| Flag | Effect |
|------|--------|
| `--proxies` | enable Browserbase residential proxies |
| `--region <region>` | session region: `us-west-2`, `us-east-1`, `eu-central-1`, `ap-southeast-1` |
| `--advanced-stealth` | advanced stealth mode |
| `--solve-captchas` / `--no-solve-captchas` | toggle automatic CAPTCHA solving |
| `--block-ads` | ad blocking |
| `--keep-alive` | keep the session alive after disconnection |
| `--session-timeout <seconds>` | session timeout |
| `--connect <session-id>` | connect to an existing Browserbase session by ID |

Also global (not remote-specific): `--session <name>` for named parallel daemon sessions, `--ws <url|port>` to target a specific CDP endpoint directly, `--headless` / `--headed`, `--json`.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BROWSERBASE_API_KEY` | For remote mode | API key from https://browserbase.com/settings; makes Browserbase the default desired environment |
| `BROWSE_SESSION` | No | Default session name (alternative to `--session`) |
| `BROWSERBASE_PROJECT_ID` | No | Passed through to Browserbase when set |

### Setting credentials

```bash
export BROWSERBASE_API_KEY="bb_live_..."
```

Get this value from https://browserbase.com/settings.

---

## Error Messages

**"No active page"**
- The daemon is running but has no page open.
- Fix: Run `browse open <url>`. If the issue persists, run `browse stop` and retry. For zombie daemons: `pkill -f "browse.*daemon"`.

**"Chrome not found"** / **"Could not find local Chrome installation"**
- The daemon tried to launch a local browser, meaning the environment did not resolve to Browserbase.
- Fix: Set `BROWSERBASE_API_KEY`, run `browse env remote`, then `browse open <url>` (no local browser needed). This skill does not drive local Chrome - for local automation use the `agent-browser` skill.

**"Daemon not running"**
- No daemon process is active. Most commands auto-start the daemon, but `snapshot`, `click`, etc. require an active session.
- Fix: Run `browse open <url>` to start a session.

**Element ref not found (e.g., "@0-5")**
- The ref from a previous snapshot is no longer valid (page changed).
- Fix: Run `browse snapshot` again to get fresh refs.

**Timeout errors**
- The page took too long to load or an element didn't appear.
- Fix: Try `browse wait load` before interacting, or raise `--timeout` on `open` / `wait`.
