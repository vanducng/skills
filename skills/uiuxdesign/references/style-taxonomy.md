# Style Taxonomy

A style vocabulary to commit to a deliberate point of view (see `design-quality.md` on intentionality). Pick one primary style per product; do not blend randomly. Each entry lists where it earns its keep and where it actively hurts.

## Selection workflow

1. **Classify the product** - what it is (SaaS, dashboard, e-commerce, portfolio, tool, mobile app), who uses it, in what context.
2. **Pick the style** from the tables below whose *Best for* matches and whose *Avoid* does not describe your product.
3. **Derive tokens** - pull a palette from `palettes-and-fonts.md` (by product type) and a font pairing (by mood). Set radius/shadow/motion from the style's technical notes.
4. **Sanity-check accessibility** - low-contrast styles (neumorphism, glassmorphism, aurora, vaporwave) need explicit 4.5:1 verification before shipping.

Native-integration overrides all of this: inside an existing app, match its design language instead of importing a bold style.

## Core web/app styles

| Style | Best for | Avoid for | Signature tokens |
|---|---|---|---|
| Minimalism / Swiss | Enterprise, dashboards, docs, SaaS, pro tools | Playful/entertainment brands, artistic portfolios | radius 0, no shadow, 12-16 col grid, single accent, WCAG AAA |
| Flat design | Web/mobile apps, MVPs, cross-platform, user-friendly SaaS | Luxury/premium, immersive 3D, artistic | solid fills, no gradients/shadows, bold color blocks |
| Glassmorphism | Modern SaaS, financial dashboards, lifestyle, modal overlays | Low-contrast backgrounds, perf-limited, a11y-critical | `backdrop-filter: blur(10-20px)`, translucent white 15-30%, 1px light border |
| Neumorphism | Health/wellness, meditation, minimal-interaction UIs | Data-heavy dashboards, a11y-critical (low contrast) | dual soft shadows, radius 12-16px, monochrome pastel |
| Claymorphism | Education, kids, creative tools, fun SaaS | Formal corporate, data-critical | puffy 3D, large radius, soft double shadow, playful color |
| Brutalism / Neubrutalism | Design portfolios, Gen-Z brands, editorial, counter-culture | Corporate, healthcare, finance, a11y-critical | radius 0, no transitions, visible 2-4px borders, bold 700+ type, primary colors |
| Bento grid | Product/feature pages, dashboards, Apple-style marketing | Dense tables, long-form text, real-time monitoring | modular card grid, varied tile sizes, generous gaps |
| Dark mode (OLED) | Night apps, coding platforms, entertainment | Print-first, high-brightness outdoor | true-black bg, desaturated accents, elevated surfaces |
| Aurora / gradient mesh | Modern SaaS, creative, music, branding | Data-heavy, a11y-critical, content-first | animated mesh gradients, vibrant hues, soft blur |
| Soft UI evolution | Modern enterprise/SaaS, health/wellness | Extreme minimalism, systems without depth | gentle shadows, medium radius, tonal palette |
| Hero-centric | SaaS landing, product launches, B2B landing | Complex multi-page nav, data-heavy apps | one dominant hero, big type, single CTA above fold |
| Editorial / magazine grid | News, blogs, journalism, long-form | Dashboards, apps, real-time data | multi-column grid, serif headlines, strong hierarchy |
| Swiss Modernism 2.0 | Corporate, architecture, editorial, museums | Playful/kids, gaming, entertainment | strict grid, restrained palette, precise typography |

## Expressive / niche styles (use deliberately)

| Style | Best for | Avoid for |
|---|---|---|
| 3D & Hyperrealism | Gaming, product showcase, high-end e-commerce, AR/VR | Low-end mobile, a11y-critical, data/forms |
| Cyberpunk / HUD / Sci-Fi FUI | Gaming, crypto, cybersecurity, sci-fi | Corporate, healthcare, family, calm-trust products |
| Vibrant block-based | Startups, creative agencies, youth/social | Finance, healthcare, government, conservative |
| Y2K / Vaporwave / Memphis | Fashion, music, Gen-Z, nostalgia marketing | B2B, healthcare, finance, education |
| Organic / biophilic / nature-distilled | Wellness, sustainability, eco, meditation | Tech/gaming, industrial, data grids |
| Retro-futurism / vintage analog | Gaming, music/vinyl, nostalgia brands | Conservative industries, a11y-critical, modern SaaS |
| Motion-driven / kinetic typography / parallax | Portfolios, storytelling, launches, interactive | Data dashboards, a11y-critical, SEO/reading-critical |
| Pixel art / E-ink-paper / terminal-CLI | Indie games, reading apps, dev/Web3 tools | Modern corporate SaaS, high-res photography |
| AI-native UI | AI products, chatbots, copilots, voice | Traditional forms, data-heavy dashboards |

## Dashboard sub-styles

When the product is analytics, match the dashboard flavor:

- **Data-dense** - BI, financial analytics, enterprise reporting. High information density, muted chrome.
- **Executive** - C-suite summaries. Few big numbers, generous whitespace.
- **Real-time monitoring** - DevOps/ops. Live tiles, status color, alert emphasis.
- **Drill-down analytics** - funnels, product analytics. Progressive disclosure, hierarchy.
- **Comparative** - period-over-period, A/B. Side-by-side, delta indicators.

## Anti-slop rules

- No emoji as structural icons - use an SVG icon set (Lucide/Heroicons) with consistent stroke width.
- Don't mix flat and skeuomorphic randomly; keep one elevation/shadow scale.
- One primary CTA per screen; secondary actions visually subordinate.
- Avoid one-hue palettes and decorative orb/gradient backgrounds unless the domain calls for it.
- Design light and dark variants together; never invert colors for dark mode - use desaturated tonal variants and re-check contrast.
