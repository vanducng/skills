---
name: show-off
description: "Create polished self-contained HTML showcase pages and section screenshots for demos, launch posts, social media, article illustrations, and visual presentations. Use when the user wants to turn a project, feature, case study, markdown brief, or prompt into a bilingual scrollable showcase with reusable promo images."
category: utilities
keywords: [html, showcase, demo, presentation, social, launch]
argument-hint: "[markdown-or-prompt]"
license: MIT
metadata:
  author: vanducng
  version: "1.0.0"
---

# Show Off

Build a polished showcase package: concise content, a self-contained HTML page,
and section screenshots in horizontal, vertical, and square ratios.

## Scope

Use this skill for:

- Project, feature, launch, demo, and case-study showcases
- Social images or article illustrations generated from HTML sections
- Bilingual Vietnamese/English promo pages
- Interactive visual presentations that can be opened locally or published later

Use `vd:copywriting` first when the content needs conversion copy or a stronger
voice. Use `vd:opendesign` for the HTML artifact. Use `vd:marketing-design` when
the showcase needs generated brand assets, logos, banners, or poster prompts.

## Workflow

1. Analyze the request and split it into 2-6 sections, including an eye-catching
   hero section.
2. If the request contains time-sensitive claims, launches, stats, news, or
   third-party facts, browse and cite current sources before writing.
3. Write showcase content to `assets/showoff/<mission-name>/content.md`.
   Include section outline, English copy, Vietnamese copy, and references.
4. Generate a self-contained HTML page with `vd:opendesign`. The first viewport
   must signal the showcased project/product clearly and hint at the next
   section.
5. Ensure the HTML supports:
   - Vietnamese characters
   - System/light/dark theme toggle when appropriate
   - Responsive layouts for 16:9, 9:16, and 1:1 captures
   - Section IDs suitable for screenshot capture, such as `#hero,#problem,#demo`
6. Capture section images with this skill's parallel capture script.
7. Open the HTML page for review when a local browser is available.

## Writing Style

Look for project writing styles in this order and use them when present:

```text
./assets/writing-styles/
~/www/writing-styles/
~/writing-styles/
```

If none exist, use clear launch/demo copy without invented claims.

## Capture Script

Resolve the script path from the installed skill directory:

```bash
SHOW_OFF_DIR="<dir-of-this-SKILL.md>"
cd "$SHOW_OFF_DIR/scripts"
npm install
node capture-sections.js \
  --url "file:///path/to/index.html" \
  --output-dir "/path/to/assets/showoff/<mission-name>/images" \
  --sections "#hero,#section-2,#section-3" \
  --ratios "horizontal,vertical,square" \
  --settle-delay 1500
```

The script captures:

- `horizontal`: 1920 x 1080
- `vertical`: 1080 x 1920
- `square`: 1080 x 1080

Options:

- `--url` required page URL
- `--output-dir` required destination
- `--sections` required comma-separated CSS selectors
- `--ratios` default `horizontal,vertical,square`
- `--settle-delay` default `1500`; alias `--delay`
- `--render-timeout` default `15000`
- `--format` default `png`
- `--quality` default `90`
- `--max-size` default `5` MB before optional compression

Fallback: if local Puppeteer capture fails and `rws` is on `PATH` with
`RWEB_API_KEY` set, use ReviewWeb screenshots only for publicly reachable URLs.
Never pass `RWEB_API_KEY` on the command line.

## Output Requirements

- Every section fits within target viewports without clipped content.
- Screenshots are named with ratio prefixes, for example `horizontal-hero.png`.
- HTML does not contain API keys, credentials, private data, or unpublished
  customer information.
- Citations appear in both `content.md` and the HTML when external facts are used.
