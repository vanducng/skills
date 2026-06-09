# Mockup-first design workflow

Design the look BEFORE app code, so the frontend has a fixed contract to build against. Two design skills, two jobs:

| Need | Skill | Output |
|------|-------|--------|
| Logo / brand mark, favicons, CIP, social/banner art (raster) | **`marketing-design`** | PNG/SVG mark + favicon set + brand assets |
| HTML page mockups, dashboards, landing/portal screens, slide decks | **`open-design`** | Self-contained HTML pages + a shared `theme.css` |
| Tailwind/shadcn token system, component code | `ui-styling` (optional) | CSS vars / components |

`marketing-design` explicitly defers HTML/dashboards/decks to `open-design`. Use both.

## Step 1 — brand mark (marketing-design)
- Generate the logo: `marketing-design` → "design logo" (style/palette/industry) or "create CIP".
- Engine = Codex `gpt-image-2` (ChatGPT subscription, `codex login`); falls back to Gemini (`GEMINI_API_KEY`).
- To stay faithful to an EXISTING logo, attach it as a reference image: the wrapper defers img2img, so call `codex exec` directly: `printf '%s' "$imagegen <prompt>... Save to ./generated.png" | codex exec --skip-git-repo-check --sandbox workspace-write -C <tmp> -o <tmp>/last.txt -i <ref.png>` (the `-i/--image` flag is variadic — pipe the prompt via stdin so it isn't swallowed).
- A hand-authored SVG is often the better portal logo (crisp, themeable). Render favicons from it with `rsvg-convert` / ImageMagick.

## Step 2 — page mockups + theme (open-design)
- Use `open-design` to produce the key screens (login, overview/dashboard, data table, detail, admin) and an `index.html` gallery.
- Produce ONE `theme.css` = the source of truth: color tokens (brand scale + ink/neutral + semantic), type scale (font + sizes/weights), spacing, radius, shadows, and component classes (buttons, cards, badges, tables, sidebar, status chips). The brand color is the accent (~10% of UI), not large fills.
- Save under `.work/visuals/` (umbrella) or `plans/visuals/`: `index.html`, `screens/*.html`, `assets/theme.css`, `assets/logo/*`.

## Step 3 — approve direction (gate)
Before building, present the visual direction with `AskUserQuestion` (use `preview` options with small ASCII/code mockups). Lock: style/mood, screen list, scope, logo treatment. Cheap to change now, expensive after code.

## Step 4 — port the theme into the React app
- Map `theme.css` tokens to shadcn HSL CSS vars in `src/index.css` (`--primary` = brand, `--background`, `--foreground`, `--border`, `--radius`) and keep raw brand tokens (`--brand`, ink scale).
- Hand-write shadcn-style `components/ui/*` (Radix + cva) styled to the tokens.
- Build each screen to MATCH the mockup. Re-screenshot the running app (Puppeteer or agent-browser) and diff against the mockup; fix drift.

## Brand lockup gotcha
If the wordmark stacks under/next to the icon via CSS grid (icon col1, name row1, tagline row2), the wordmark wrapper element needs `display: contents` so its children become grid items — otherwise the tagline renders inline next to the name. See `gotchas.md`.

## Docs / help pages
- Put the table-of-contents on the RIGHT rail (content left), sticky on wide screens, hidden/stacked on narrow. A left TOC reads awkwardly.
- Manage help content as Markdown (react-markdown + remark-gfm), auto-generate the TOC from headings.
- Keep client/tenant docs free of internal role tables and audit internals (those are internal-only).
- Realign multi-step "how it works" blocks (number + label column, description column) so labels don't wrap awkwardly.

## Copy rules
- No em-dash (—) in UI copy; use ", " or " - " or rephrase. Scan components for "—" before shipping.
- Keep one support email / brand string in a single constant.
- Client-facing precision: describe the user's real action ("upload hire data from your ATS"), avoid internal jargon and over-claims, and don't leak infra specifics (cloud "S3", not bucket names). See gotchas #18.
