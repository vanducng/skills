---
name: uiuxdesign
description: "UI/UX design quality across interfaces — visual design, UX review, accessibility audits, design systems, and design critique — plus modern web frontend implementation. Use for design-quality scoring and refactor loops, design reviews, style selection (40+ named styles), color palettes and font pairing by product type, shadcn/ui and Tailwind theming, responsive UI, visual polish, design tokens, Next.js or React implementation, TanStack Router/Query/Form/Table/Start, Playwright/Vitest web testing, Core Web Vitals, dashboards, forms, data tables, charts, landing pages, product pages, and optional Three.js/WebGL/WebGPU scenes."
license: MIT
metadata:
  author: vanducng
  version: "1.0.0"
---

# UI/UX Design

Drive UI/UX design quality across any interface — aesthetic direction, UX review, accessibility, design systems, and adversarial design critique — and implement it in a modern web stack. This skill consolidates design quality, anti-slop aesthetics, a render-score-refactor review loop, frontend framework choices, TanStack patterns, web testing, and optional Three.js work into one workflow. Top identity is design quality; web implementation is how it lands.

## Reference Router

Read only what the task needs:

- `references/design-quality.md`: visual design, UX review, accessibility, responsive layout, typography, forms, charts, and polish checks.
- `references/style-taxonomy.md`: 40+ named styles with best-for/avoid guidance, dashboard sub-styles, and the product → style → tokens selection workflow.
- `references/palettes-and-fonts.md`: semantic-token color palettes by product type and Google-Font pairings by mood (with CJK/RTL coverage).
- `references/tailwind-shadcn.md`: shadcn/ui + Tailwind idioms — setup, CSS-variable theming, dark mode, responsive, component/form/table patterns, and the Web Interface Guidelines review pass.
- `references/app-frameworks.md`: React, Next.js App Router, Server/Client Components, caching, monorepos, icons, and frontend architecture.
- `references/tanstack.md`: TanStack Router, Query, Form, Table, Start, and when to choose them.
- `references/testing.md`: Vitest, Testing Library, Playwright, accessibility, visual regression, performance, cross-browser, CI, and release checks.
- `references/threejs.md`: Three.js, GLTF, WebGL/WebGPU, animations, interaction, performance, and browser verification.

## Workflow

1. Inspect the existing app before choosing patterns: package manager, framework, route layout, component library, design tokens, icons, tests, and current visual conventions.
2. Classify the task:
   - **Design/review:** load `design-quality.md`.
   - **Choosing a style, palette, or fonts:** load `style-taxonomy.md` and `palettes-and-fonts.md`.
   - **Building/theming shadcn + Tailwind components:** load `tailwind-shadcn.md`.
   - **React/Next/framework architecture:** load `app-frameworks.md`.
   - **TanStack feature:** load `tanstack.md`.
   - **Tests, QA, a11y, performance, or release validation:** load `testing.md`.
   - **3D/WebGL/WebGPU/canvas scene:** load `threejs.md`.
3. Build within the app's existing system. Reuse local components, tokens, layout primitives, routing conventions, and icon library before adding dependencies.
4. Verify behavior in the browser whenever a visual surface changes. Check desktop and mobile widths, keyboard flow, focus visibility, reduced motion, loading/error/empty states, and console errors.
5. Run the repo's narrowest relevant validation first, then the broader test/build command expected by the project.

## Design Defaults

- **Quality target = 9/10 by default** (not perfectionist 9.5). Reach a 9 and stop unless the user explicitly demands more — then warn about diminishing returns. See `references/design-quality.md` for the render → screenshot → score → refactor loop and the adversarial critic panel.
- **Commit to a point of view** before coding: purpose, tone, and the one thing someone will remember. Intentionality over intensity — refined minimalism and bold maximalism both work when executed deliberately. Full aesthetic and anti-slop rules in `references/design-quality.md`.
- **Native-integration wins.** When the UI must feel native to an existing app (internal/operator tools especially), match its design language and component library — the "be bold/distinctive" default yields to native consistency.
- Make the requested usable experience the first screen. Do not build a marketing landing page when the user asked for an app, dashboard, game, editor, or tool.
- Use real product, data, or interaction signals in the first viewport. Avoid generic decorative backgrounds when the user needs to inspect the thing.
- Keep operational tools quiet and dense: predictable navigation, scan-friendly tables, restrained color, compact headings, and repeatable workflows.
- Use semantic HTML and accessible component primitives. Icon-only controls need accessible names and visible focus states.
- Prefer familiar icons over text labels for compact tool actions. Use the app's icon library; if none exists and adding one is acceptable, prefer `lucide-react`.
- Do not use emojis as structural UI icons.
- Use stable dimensions for boards, grids, toolbars, icon buttons, tiles, counters, and canvases so hover, loading, and dynamic content do not shift layout.
- Avoid text overlap, horizontal scroll, clipped labels, and viewport-scaled font sizes. Text should wrap before it overflows.
- Avoid one-hue palettes and decorative gradient/orb backgrounds unless the product domain genuinely calls for them.

## Framework Defaults

- For Next.js App Router, keep pages/layouts as Server Components by default. Add `"use client"` only at interactive leaves that need state, events, effects, browser APIs, or custom client hooks.
- In current Next.js projects using Cache Components, prefer explicit caching with `cacheComponents`, `"use cache"`, `cacheLife`, and `cacheTag` over older implicit caching assumptions.
- Do not put secrets, direct database clients, or server-only utilities into client bundles.
- For TanStack apps, route structure is the contract. Keep generated route trees generated, model URL state deliberately, and use Query for server state rather than hand-rolled fetch caches.
- For large tables, pair TanStack Table with virtualization, stable column definitions, keyboard-accessible controls, and clear empty/loading/error states.

## Verification Floor

Before handoff for any frontend change, report what you ran and what remains unverified:

- Static checks: typecheck, lint, unit/component tests, or the repo's closest equivalent.
- Browser checks: at least one desktop and one mobile viewport for visual changes.
- Accessibility checks: keyboard path, focus visibility, labels/names, contrast, reduced motion, and no color-only meaning.
- Runtime checks: no console errors, no layout shift from async content, loading/error/empty states present.
- Performance checks when relevant: image dimensions, lazy loading, bundle impact, and Core Web Vitals risk (LCP, CLS, INP).
- 3D checks when relevant: nonblank canvas, correct camera framing, resize behavior, animation loop health, disposal of resources, and fallback/error state for unsupported GPU features.

## Hard Rules

- Do not preserve old source skill names, runtime prefixes, or Claude-specific paths in new work.
- Do not paste huge reference dumps into `SKILL.md`; route to references.
- Do not introduce a new design system when the app already has one unless the task explicitly asks for redesign.
- Do not skip browser verification after meaningful visual, layout, or 3D changes.
- Do not rely only on automated accessibility tooling; combine tooling with manual keyboard and screen-reader-oriented checks.
