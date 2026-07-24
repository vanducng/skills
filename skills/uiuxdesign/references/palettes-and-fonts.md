# Palettes & Font Pairings

Starter design tokens by product type and mood. These are opinionated defaults to derive `--primary`/`--background`/etc. from, not laws - adapt to the brand. All palettes are tuned so the accent clears WCAG 3:1 against its background; re-verify any pair you change.

## Color palettes (semantic tokens by product type)

Columns map to the common CSS-variable set: `primary` / `secondary` / `accent` / `background` / `foreground` / `muted` / `border` / `destructive`.

| Product type | Primary | Secondary | Accent | Background | Foreground | Muted | Border | Destructive |
|---|---|---|---|---|---|---|---|---|
| SaaS (general) | `#2563EB` | `#3B82F6` | `#EA580C` | `#F8FAFC` | `#1E293B` | `#E9EFF8` | `#E2E8F0` | `#DC2626` |
| Micro SaaS | `#6366F1` | `#818CF8` | `#059669` | `#F5F3FF` | `#1E1B4B` | `#EBEFF9` | `#E0E7FF` | `#DC2626` |
| B2B service | `#0F172A` | `#334155` | `#0369A1` | `#F8FAFC` | `#020617` | `#E8ECF1` | `#E2E8F0` | `#DC2626` |
| E-commerce | `#059669` | `#10B981` | `#EA580C` | `#ECFDF5` | `#064E3B` | `#E8F1F3` | `#A7F3D0` | `#DC2626` |
| E-commerce luxury | `#1C1917` | `#44403C` | `#A16207` | `#FAFAF9` | `#0C0A09` | `#E8ECF0` | `#D6D3D1` | `#DC2626` |
| Analytics dashboard | `#1E40AF` | `#3B82F6` | `#D97706` | `#F8FAFC` | `#1E3A8A` | `#E9EEF6` | `#DBEAFE` | `#DC2626` |
| Financial dashboard (dark) | `#0F172A` | `#1E293B` | `#22C55E` | `#020617` | `#F8FAFC` | `#1A1E2F` | `#334155` | `#EF4444` |
| Fintech / crypto | `#F59E0B` | `#FBBF24` | `#8B5CF6` | `#0F172A` | `#F8FAFC` | `#272F42` | `#334155` | `#EF4444` |
| AI / chatbot | `#7C3AED` | `#A78BFA` | `#0891B2` | `#FAF5FF` | `#1E1B4B` | `#ECEEF9` | `#DDD6FE` | `#DC2626` |
| Developer tool / IDE (dark) | `#1E293B` | `#334155` | `#22C55E` | `#0F172A` | `#F8FAFC` | `#272F42` | `#475569` | `#EF4444` |
| Cybersecurity (dark) | `#00FF41` | `#0D0D0D` | `#FF3333` | `#000000` | `#E0E0E0` | `#181818` | `#1F1F1F` | `#EF4444` |
| Educational | `#4F46E5` | `#818CF8` | `#EA580C` | `#EEF2FF` | `#1E1B4B` | `#EBEEF8` | `#C7D2FE` | `#DC2626` |
| Beauty / spa / wellness | `#EC4899` | `#F9A8D4` | `#8B5CF6` | `#FDF2F8` | `#831843` | `#F1EEF5` | `#FBCFE8` | `#DC2626` |
| Creative / marketing agency | `#EC4899` | `#F472B6` | `#0891B2` | `#FDF2F8` | `#831843` | `#F1EEF5` | `#FBCFE8` | `#DC2626` |
| Food delivery / on-demand | `#EA580C` | `#F97316` | `#2563EB` | `#FFF7ED` | `#0F172A` | `#FDF4F0` | `#FCEAE1` | `#DC2626` |
| Gaming (dark) | `#7C3AED` | `#A78BFA` | `#F43F5E` | `#0F0F23` | `#E2E8F0` | `#27273B` | `#4C1D95` | `#EF4444` |

Reading the choices: trust domains (SaaS, B2B, fintech) lean blue/navy primary with a warm CTA accent; commerce leans green/urgency-orange; creative/beauty leans pink + a cool secondary; dev/finance/gaming go dark-background with a single vivid status accent. Pick the row nearest your product, then nudge hues toward the brand.

## Font pairings (by mood)

Heading + body pairing, all Google Fonts. Match the heading/body personalities; don't pair two loud display faces. Single-family rows (Inter/Inter) use weight for hierarchy.

| Pairing | Heading | Body | Mood | Best for |
|---|---|---|---|---|
| Classic elegant | Playfair Display | Inter | elegant, luxury, timeless, editorial | Luxury, fashion, spa, editorial, high-end e-commerce |
| Modern professional | Poppins | Open Sans | modern, clean, corporate, friendly | SaaS, corporate, business apps, startups |
| Tech startup | Space Grotesk | DM Sans | tech, innovative, bold, futuristic | Startups, dev tools, AI products |
| Minimal Swiss | Inter | Inter | minimal, functional, neutral | Dashboards, admin, docs, design systems |
| Friendly SaaS | Plus Jakarta Sans | Plus Jakarta Sans | friendly, approachable, professional | SaaS, web apps, B2B, productivity |
| Geometric modern | Outfit | Work Sans | geometric, contemporary, balanced | General purpose, portfolios, agencies |
| Premium sans | Satoshi | General Sans | premium, sophisticated, versatile | Premium brands, modern agencies, startups |
| Developer mono | JetBrains Mono | IBM Plex Sans | code, technical, precise | Dev tools, docs, code editors, tech blogs |
| Editorial classic | Cormorant Garamond | Libre Baskerville | literary, traditional, refined | Publishing, blogs, literary magazines |
| News editorial | Newsreader | Roboto | journalism, trustworthy, readable | News, magazines, content-heavy sites |
| Corporate trust | Lexend | Source Sans 3 | trustworthy, accessible, readable | Enterprise, government, healthcare, finance |
| Wellness calm | Lora | Raleway | calm, natural, organic | Health, wellness, spa, meditation, yoga |
| Luxury serif | Cormorant | Montserrat | luxury, high-end, refined | Fashion, luxury e-commerce, jewelry |
| Fashion forward | Syne | Manrope | avant-garde, artistic, editorial | Fashion, creative agencies, art galleries |
| Bold statement | Bebas Neue | Source Sans 3 | bold, dramatic, headline | Marketing, portfolios, event pages, sports |
| Playful creative | Fredoka | Nunito | playful, fun, warm | Kids apps, education, gaming, creative tools |
| Soft rounded | Varela Round | Nunito Sans | soft, friendly, gentle | Kids/pet apps, friendly brands, wellness |
| Brutalist raw | Space Mono | Space Mono | raw, technical, stark | Brutalist designs, dev portfolios, experimental |
| Retro vintage | Abril Fatface | Merriweather | nostalgic, decorative, dramatic | Vintage brands, breweries, creative portfolios |

**CJK / RTL:** use the Noto family for multilingual coverage - Noto Serif/Sans JP (Japanese), Noto Sans KR (Korean), Noto Serif/Sans SC/TC (Simplified/Traditional Chinese), Noto Naskh + Noto Sans Arabic (RTL), Noto Sans Thai/Hebrew. Be Vietnam Pro pairs well for Vietnamese.

## Applying tokens

- Load fonts with `display: swap` and `font-preload` only the critical face; reserve space to avoid layout shift.
- Base body 16px, line-height 1.5–1.75, measure 60–75 chars desktop / 35–60 mobile.
- Type scale: 12 · 14 · 16 · 18 · 24 · 32 (extend up as needed); weight carries hierarchy - 400 body, 500 labels, 600–700 headings.
- Never hardcode raw hex in components; map these to semantic tokens (`--primary`, `--muted-foreground`, …) and theme light/dark separately.
