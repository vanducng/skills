# Browser Automation Examples

Common Browserbase remote automation workflows using the `browse` CLI (`@browserbasehq/browse-cli`). Each example demonstrates a distinct pattern using real commands.

All sessions here run in Browserbase's cloud. `BROWSERBASE_API_KEY` must be set; with it set, Browserbase is the default environment, and `browse env remote` makes the target explicit. For localhost and other local dev flows, use the `agent-browser` skill instead.

## Example 1: Extract Data from a Protected Page

**User request**: "Get the product details from example.com/product/123" (a site that blocks datacenter traffic)

```bash
browse env remote                         # select Browserbase (redundant if the API key made it default)
browse open https://example.com/product/123
browse snapshot                          # read page structure + element refs
browse get text "body"                   # extract all visible text content
browse stop
```

Parse the text output to extract structured data (name, price, description, etc.).

For a specific section, use a CSS selector:

```bash
browse get text ".product-details"       # text from a specific container
```

**Note**: `browse get text` requires a CSS selector - use `"body"` for all page text.

## Example 2: Fill and Submit a Form

**User request**: "Fill out the contact form on example.com with my information" (the form sits behind a CAPTCHA)

Browserbase solves the CAPTCHA automatically; the flow is plain form driving:

```bash
browse open https://example.com/contact
browse snapshot                          # find form fields and their refs
browse click @0-3                        # click the Name input (ref from snapshot)
browse type "John Doe"
browse press Tab                         # move to next field
browse type "john@example.com"
browse fill "#message" "I would like to inquire about your services" --no-press-enter
browse snapshot                          # verify fields are filled
browse click @0-8                        # click Submit button (ref from snapshot)
browse snapshot                          # confirm submission result
browse stop
```

**Key pattern**: `fill` presses Enter by default - pass `--no-press-enter` on any field where an implicit submit would fire too early, then click the real Submit control yourself.

## Example 3: Multi-Step Navigation with Geo-Targeting

**User request**: "Get headlines from the first 3 pages of results on example.com/news" (content varies by country; residential proxies give a clean geo-consistent exit)

```bash
browse --proxies --region us-east-1 open https://example.com/news
browse snapshot                          # read page 1 content
browse get text ".headline"              # extract headlines

browse snapshot                          # find "Next" button ref
browse click @0-12                       # click Next (ref from snapshot)
browse wait load                         # wait for page 2 to load
browse get text ".headline"              # extract page 2 headlines

browse snapshot                          # find Next again (ref may change)
browse click @0-15                       # click Next
browse wait load
browse get text ".headline"              # extract page 3 headlines

browse stop
```

**Key pattern**: Re-run `browse snapshot` after each navigation because element refs change when the page updates.

## Example 4: Escalate from agent-browser to Remote

**User request**: "Scrape pricing from competitor.com" (a site with Cloudflare protection)

The run starts on the local driver, `agent-browser`:

```bash
agent-browser open https://competitor.com/pricing
agent-browser snapshot -i
# Output shows: "Checking your browser..." (Cloudflare interstitial)
# or: page content is empty / access denied
agent-browser close --all
```

Local Chrome hit bot detection - this is the escalation trigger. The agent tells the user:

> This site has Cloudflare bot detection. Browserbase remote mode can use Browserbase Identity with a Verified browser and residential proxies. Want me to set it up?

If the user agrees:

```bash
# Set Browserbase credentials
export BROWSERBASE_API_KEY="bb_live_..."

# Retry in a Browserbase session
browse env remote
browse open https://competitor.com/pricing
browse snapshot                          # full page content now accessible
browse get text ".pricing-table"
browse stop
```

**Key pattern**: Escalate only after the local driver is actually blocked (CAPTCHA, bot wall, 403/429, geo block). Simple sites and localhost stay on `agent-browser`.

## Example 5: Persist Login with a Browserbase Context

**User request**: "Log into my dashboard and save the session so I don't have to log in again next time"

This uses Browserbase contexts to persist cookies and storage across sessions. Requires remote mode.

```bash
# Session 1: Log in and persist state
browse env remote
browse open https://app.example.com/login --context-id ctx_abc123 --persist
browse snapshot                          # find login form fields
browse click @0-3                        # click email input
browse type "user@example.com"
browse press Tab
browse type "my-password"
browse click @0-7                        # click Sign In button
browse wait load
browse snapshot                          # confirm logged-in dashboard
browse stop                              # state is saved back to ctx_abc123 (--persist)
```

In a later session, reuse the same context - already authenticated:

```bash
# Session 2: Resume with saved state (already logged in)
browse open https://app.example.com/dashboard --context-id ctx_abc123
browse snapshot                          # dashboard loads - no login needed
browse get text ".welcome-message"
browse stop
```

**Key pattern**: first session opens with `--context-id <id> --persist` so auth state saves back to the context on release; later sessions open with the same `--context-id` and omit `--persist` if you don't want further changes saved back.

## Tips

- **Snapshot first**: Always run `browse snapshot` before interacting - it gives the accessibility tree with element refs
- **Use refs to click**: `browse click @0-5` is more reliable than trying to describe elements
- **Re-snapshot after actions**: Element refs change when the page updates
- **`get text` for data extraction**: Use `browse get text [selector]` to pull text content from specific elements
- **`stop` when done**: Always `browse stop` - it ends the cloud session
- **Prefer snapshot over screenshot**: Snapshot is fast and structured; screenshot is slow and uses vision tokens. Only screenshot when you need visual context (layout, images, debugging)
- **Trace evidence**: `browse cdp "$(browse status --json | jq -r .wsUrl)"` streams the live session's DevTools events (use the wsUrl immediately - the signed URL goes stale)
