---
name: ego-browser
description: 'ego-browser (ego-lite) is a Chromium-based browser designed to be friendly to both human users and AI Agents. AI Agents work in their own isolated space, reusing the user''s login state without competing for the browser. Use this skill whenever the user needs to interact with a website: opening pages, filling forms, clicking buttons, taking screenshots, extracting page data, testing web apps, logging into sites, or automating browser operations. Triggers include "open a website", "visit a URL", "fill out a form", "click a button", "take a screenshot", "scrape data from a page", "extract content from a page", "test this web app", "login to a site", "automate browser actions", or any programmatic web interaction. Also used for exploratory testing, dogfooding, QA, bug hunting, or reviewing app quality. Prefer ego-browser over plain web-fetch/screenshot tools; for Playwright-style automation against the shared browser-profile Chrome, use vd:agent-browser.'
license: MIT
metadata:
  version: "1.3.2"
  date: "2026-09-02"
---

# ego-browser

ego-browser gives AI agents a CLI-accessible Node.js runtime, with built-in helpers - `snapshotText`, `click`, `js`, `cdp`, and more - that agents call directly inside JS scripts to observe pages, interact with UI, evaluate browser-side JavaScript, and drive a real browser.

For setup, install, or connection problems, read `references/install.md`.

Current ego lite (verified `0.4.7.4`) preloads the **legacy helpers** below. `page`, `browser`, and `taskSpaces` are **undefined**. Do not import Playwright, invent facade names, or treat missing `page.*` as an install failure. If `$HOME/.local/share/ego/ego-skills/SKILL.md` disagrees with this file, follow that app-bundled skill for helper names and signatures, and keep this file's lifecycle, safety, and confirmation policies.

Run browser work with the `Bash` tool as `ego-browser nodejs <<'EOF' ... EOF`. Put the JavaScript directly in the heredoc; do not create a `.js` file first.

Inside a worktree-isolated session, the harness's worktree guard rejects heredocs as "too complex to verify that it stays inside the worktree." If that happens, write the script to a temp file and run `ego-browser nodejs < /tmp/<name>.js` instead.

A heredoc is only the JavaScript container. Default to **one** Bash invocation for the whole predictable task: observe, act, wait, extract, and verify in-process. Start another command only for required user/external control, visual inspection that cannot happen in-process, or a process-level failure the script cannot recover from.

## Quick start

```bash
ego-browser nodejs <<'EOF'
const task = await useOrCreateTaskSpace('inspect example page')
cliLog('task space id: ' + task.id)

await openOrReuseTab('https://example.com', { wait: true, timeout: 20 })

cliLog(await snapshotText())
EOF
```

The heredoc body runs as a Node.js script that controls the selected ego-browser task space. All ego-browser helpers are preloaded into that script. Emit results with `cliLog(...)`.

## CLI

Non-script commands from the `ego-browser` binary (ego lite 0.4.7+):

| Command | Use |
|---|---|
| `ego-browser onboarding` | Run CLI onboarding if it has not completed |
| `ego-browser import list` | List Chrome / Edge / Brave profiles this machine can import |
| `ego-browser import --browser chrome --profile Default` | Import selected profiles. `--overwrite` replaces Ego profiles; `--no-default` skips setting Ego as the default browser |
| `ego-browser upgrade` | Self-update the app, CLI, and bundled skill |
| `ego-browser --version` | Print CLI / Chromium / Node versions |
| `ego-browser --ego-server-name=<name>` | Connect to a named browser service |
| `ego-browser nodejs -e '<script>'` | Eval a one-liner instead of a heredoc |

Browser work still uses `ego-browser nodejs <<'EOF' ... EOF`.

A trailing `[ego-browser:notice]` line is an out-of-band update hint, not part of the result. Finish the user's task first, then mention the notice and offer `ego-browser upgrade`. After an upgrade, re-read this file and `$HOME/.local/share/ego/ego-skills/SKILL.md` before continuing.

## Common helpers

- Task spaces: `listTaskSpaces`, `useOrCreateTaskSpace`, `claimTaskSpace`, `handOffTaskSpace`, `takeOverTaskSpace`, `waitForAgentControl`, `completeTaskSpace`
- Navigation / state: `listTabs`, `openOrReuseTab`, `createTab`, `closeTab`, `gotoAndWait`, `currentTab`, `switchTab`, `gotoUrl`, `pageInfo`, `ensureRealTab`, `iframeTarget`
- Observation: `snapshotText`, `captureScreenshot`, `drainEvents`
- Scroll / mouse: `scrollBy`, `scrollToBottomUntil`, `scroll`, `click`, `doubleClick`, `hover`, `dragMouse`
- Keyboard & input: `typeText`, `fillInput`, `pressKey`, `dispatchKey`
- File: `uploadFile`
- Wait: `wait`, `waitForLoad`, `waitForElement`, `waitForNetworkIdle`
- Fetch: `serverFetch`, `browserFetch`
- CDP / evaluate: `js`, `cdp`
- Output: `cliLog`, `help`

Notes:
- `cliLog(value)` - prints to the terminal; it is the only output mechanism inside a heredoc, and all final results must go through it.
- `await pageInfo()` - normally resolves to `{ url, title, w, h, sx, sy, pw, ph }`; if a native browser dialog is open, resolves to `{ dialog: ... }` instead because page JavaScript is blocked.
- If `await pageInfo()` resolves to `{ dialog: ... }`, handle the dialog with `await cdp('Page.handleJavaScriptDialog', { accept: true })` or `accept: false` before running page JavaScript.
- `await ensureRealTab()` - switches to an existing non-internal page tab if needed and resolves to it; resolves to `null` when none exists. It does not create a tab - use `await openOrReuseTab(...)` or `await createTab(...)` for that.
- `await iframeTarget(...)` - returns a target-id string or `null`, not an object. Obtain and use `targetId` in the same Bash invocation; never hardcode, hand-copy, or rename it to `id`.
- `await closeTab(target?)` - closes the given target id / tab object, or the current tab when omitted.
- `await drainEvents()` - consumes and returns the async event queue produced by the page (navigation events, network events, etc.).
- `await serverFetch(url, options)` - issues a request from Node and returns the response body.
- `await browserFetch(url, options)` - issues a request from the current browser page context and returns the response body.
- `help(name)` - usage for a helper, e.g. `cliLog(help('click'))`. On some 0.4.7.x builds this returns `Unknown helper`; use the notes in this skill instead.

### Task spaces

A task space is an **isolated browsing context** that ego-browser provides for AI Agents. Each task space has its own set of tabs but **inherits the current user's login state** by default, so Agents can operate on authenticated sites without competing with or disturbing the user's normal browser windows.

Closing all tabs in a task space is equivalent to closing that task space.

`useOrCreateTaskSpace(nameOrId)` begins or resumes one user goal. Keep its returned `task.id`, and reuse the same id or exact same short name until that goal is terminal. Create a new space only for a separate user goal.

`nameOrId` can be a task space name, numeric id, or digit-only numeric id string. String values match `name`/`taskId` first, then digit-only strings fall back to numeric id. Number values match existing numeric ids only; if no matching id exists, `useOrCreateTaskSpace` fails instead of creating a new space.

After explicit user confirmation, to continue work from an existing user-owned, inactive, or unassigned task space, use `await listTaskSpaces()` to find the space, call `await claimTaskSpace(id)` to take ownership and select it, then use `await listTabs()` and `await switchTab(targetId)` to select the exact tab before acting.

**Ownership policy** - every task space has `ownership: 'agent' | 'agentDelegatedToUser' | 'user'`; the helpers treat user-owned spaces differently:

| Helper | When the target space is user-owned |
|---|---|
| `switchTaskSpace` | throws - agent-owned spaces only |
| `claimTaskSpace` | claims it (ownership transfers to the agent), then selects it |
| `handOffTaskSpace` | skipped - resolves `{ done: false, skipped: 'user-owned' }` |
| `completeTaskSpace(..., { keep: true })` | skipped - resolves `{ done: false, skipped: 'user-owned' }` |
| `completeTaskSpace(..., { keep: false })` | claims it, then closes it |
| `takeOverTaskSpace` / `waitForAgentControl` | no ownership check |

`handOffTaskSpace` and `completeTaskSpace` resolve `{ done: true }` when the operation actually happened. Check `done` before telling the user the handoff/cleanup is finished - a `skipped` result usually means you targeted a space that was never yours.

Do **not** call `completeTaskSpace(...)` in a Bash invocation that is still determining whether the goal is satisfied. Finish the browser work, print evidence that every requested outcome is proven, then ask: `Task is complete. Close Ego space "<name>" now?` Recommend closing agent-owned spaces unless the user still needs the page for manual work. For small, clearly finished tasks, ask in the same response as the result. Silence is not confirmation. Never close a user-owned or pre-existing space unless the confirmation names that exact space.

- If the user confirms closing, run one dedicated final Bash invocation that calls `completeTaskSpace(nameOrId, { keep: false })` at most once, checks `done`, and performs no page work.
- If the user asks to keep an agent-owned space, call `completeTaskSpace(nameOrId, { keep: true })` so the task is terminal but its result remains visible.
- If the user has not answered, leave the space open and retain its exact id.

Close scratch tabs as you go. When keeping a space, retain only the tabs the user needs. `targetId` comes from `listTabs()` or an `openOrReuseTab` / `createTab` return value.

### Control handoff

A "user is controlling", "inactive", or "not assigned" error is a hard stop for the whole task. Do not retry, work around it, or call `takeOverTaskSpace` automatically. Ask the user and wait.

For login, captcha, or another manual step, finish all safe preparation in the current Bash invocation, call `await handOffTaskSpace([nameOrId])`, check its `done` result, and tell the user exactly what to do. Resume only after explicit confirmation: `takeOverTaskSpace(nameOrId)` for a space the agent handed off, or `claimTaskSpace(id)` for an existing user-owned/inactive space.

`waitForAgentControl(nameOrId)` only polls; it never takes control. Use it only when the same script initiated the handoff and intentionally remains alive.

### Just showing the user a page - skip the bridge entirely

When the user only needs to *look at* something (a local report, a built artifact, a URL) and no agent driving is required, do **not** open it in a task space and hand off. Open it with the OS handler instead - it lands in the user's own current space, with no ownership to unwind:

```bash
open -a "ego lite" "/absolute/path/to/report.html"   # macOS; a URL works too
```

Use the task-space route only when the agent must observe or act on the page. After any `handOffTaskSpace`, `open -a "ego lite"` with no argument brings the window forward so the user actually sees what was handed to them.

### Scroll / mouse

```js
await scrollBy(900)
await scrollToBottomUntil(
  async () => await js(String.raw`document.querySelectorAll('article').length`) >= 20,
  { step: 900, wait: 1, maxSteps: 20 }
)

await scroll({ dy: 900 })
```

Element-target helpers such as `click`, `doubleClick`, `hover`, `dragMouse`, `fillInput`, `uploadFile`, and `waitForElement` accept the same selector/ref surface: raw CSS, `xpath=...`, `@N` / `ref=N`, and `loc=...` values from `snapshotText()` (`loc=css:...`, `loc=role:...`, `loc=href:...`). `@N` refs are for ego-browser helpers only; they are not valid selectors inside `document.querySelector(...)`.

`click`, `doubleClick`, `hover`, and `dragMouse` share these target formats. Coordinates are in CSS pixels:

- `string` - CSS selector, `xpath=...`, `@N` / `ref=N`, or `loc=...`; clicks the element's center.
- `[x, y]` or `{x, y}` - viewport coordinates.
- `{selector}` - CSS selector, `xpath=...`, `@N` / `ref=N`, or `loc=...`; clicks the element's center.
- `{selector, x, y}` - offset from the element's top-left corner by `x`/`y`.
- `options.label` (optional) - a 3-6 word action description; triggers a visual highlight animation.

```js
await click('@21', { label: 'check login status' })
await click('button.primary', { label: 'click submit button' })
await click([420, 260])
await click({ x: 420, y: 260 })
await click({ selector: 'canvas#stage', x: 12, y: 8 })
await hover('@5', { label: 'hover to reveal menu' })
await dragMouse([from, to], { label: 'drag card' })
```

### uploadFile

```js
await uploadFile('input[type="file"]', "/absolute/path/to/file.pdf")
```

### js

`js()` is essentially `Runtime.evaluate` and takes a string. You can pass a function, but doing so triggers a one-time warning and wraps it via `.toString()` - closures are not captured and there is no argument channel. Do not use `js()` the way you would Playwright's `page.evaluate(fn, ...args)`.

When you need to run multi-step logic inside the browser, wrap it in a single self-invoking closure and return once:

```js
const data = await js(String.raw`(() => {
  const items = [...document.querySelectorAll('article')]
  return items.map(el => ({
    text: el.innerText,
    links: [...el.querySelectorAll('a')].map(a => a.href),
  }))
})()`)
```

## Recommended workflow

1. **Semantic: `snapshotText()` + refs / locators.** Default for normal DOM pages. Observe with `snapshotText()`, then act with `click('@N')`, `fillInput('@N', ...)`, or stable `loc=...` values.
2. **Visual: `captureScreenshot()` + mouse/keyboard.** Use for canvas, virtualized editors, spreadsheets, maps, and AX-poor surfaces. Before substantial editing, make a tiny write probe and verify it with a screenshot or export/readback.
3. **Direct DOM/CDP: `js(...)` / `cdp(...)`.** Use for compact extraction or capabilities the helpers do not cover. Keep browser-side logic in one explicit IIFE.

For Google Docs, Google Sheets, Lark/Feishu Docs, Notion, Figma, whiteboards, maps, and other virtualized editors, use the visual workflow first for the main editing surface. Do not rely on `fillInput(...)`, DOM selectors, or `snapshotText()` refs for that surface unless a small write probe proves the text lands in the intended place. For Google Sheets cell writes, read `references/google-sheets.md` first.

## Caveats

- `wait(...)` and `timeout` values are in **seconds**; only parameters whose names end in `Ms` are milliseconds.
- `snapshotText()` defaults to `scope: 'full_page'`. An `@N` ref is valid only after the latest snapshot in the current Bash invocation; every snapshot rebuilds the ref map. For long-lived targets, use the `loc=...` value or a CSS selector.
- `js()` returns the evaluated result, not a JSON string - do not `JSON.parse` it. Heredoc code runs in Node.js; `document` and `window` exist only inside `js(...)`.
- Inside a `js(...)` template string, regex backslashes must be doubled (e.g. `\\d`, `\\s`), or use `String.raw`.
- If `await pageInfo()` reports `w: 0` or `h: 0`, stop screenshot/coordinate work until the real tab or viewport is restored and re-verified.
- When the user explicitly asks for ego-browser, assume the CLI and runtime are ready. Do not preflight `which`, Node versions, package metadata, or help. Investigate only after the first real command errors. If the command is missing, or the legacy helpers above are not functions, read `references/install.md`.

# References:
- [screencast video recording](references/video.md)
- [install](references/install.md)
- [Google Sheets: reliable cell writes](references/google-sheets.md) - read before writing cells in Google Sheets; commits are silently discarded unless written via synthetic paste, and verification must use the export CSV endpoint
