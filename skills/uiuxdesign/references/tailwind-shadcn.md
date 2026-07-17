# Tailwind + shadcn/ui Idioms

Implementation specifics for the shadcn/ui + Tailwind stack — the default for React/Next web UI in this skill. Use alongside `app-frameworks.md` (framework architecture) and `design-quality.md` (quality bar). Only reach here when actually building/theming components.

## Setup

```bash
npx shadcn@latest init          # framework, TS, paths, base color, CSS variables
npx shadcn@latest add button card dialog form input table
```

shadcn is copy-paste distribution: components land in your repo (`components/ui/`), you own and edit them. There is no runtime dependency to upgrade — re-run `add` to pull newer versions. Prefer a shadcn/ui MCP (if connected) to search components and examples before hand-rolling.

Tailwind-only (no shadcn), Vite:

```bash
npm install -D tailwindcss @tailwindcss/vite
```
```css
/* index.css */  @import "tailwindcss";
```

## Theming with CSS variables

shadcn themes through HSL CSS variables mapped to Tailwind semantic colors. Define both themes together and let `.dark` (or `[data-theme=dark]`) override:

```css
:root {
  --background: 0 0% 100%;
  --foreground: 222 47% 11%;
  --primary: 221 83% 53%;
  --primary-foreground: 0 0% 100%;
  --muted: 210 40% 96%;
  --muted-foreground: 215 16% 47%;
  --border: 214 32% 91%;
  --destructive: 0 72% 51%;
  --radius: 0.5rem;
}
.dark {
  --background: 222 47% 4%;
  --foreground: 210 40% 98%;
  --primary: 217 91% 60%;
  --muted: 217 33% 17%;
  --muted-foreground: 215 20% 65%;
  --border: 217 33% 20%;
}
```

Rules: components reference `bg-primary text-primary-foreground`, never raw hex. Dark mode uses desaturated/lighter tonal variants, not inverted light values, and its contrast is verified independently. Seed the variables from a `palettes-and-fonts.md` row.

## Dark mode toggle (Next.js)

Use `next-themes`; wrap the app in `ThemeProvider` with `attribute="class"`, and gate the toggle button on `mounted` to avoid hydration mismatch. Respect `prefers-color-scheme` as the default.

## Responsive

Mobile-first: unprefixed utilities are the base, then layer `sm: md: lg: xl: 2xl:` (defaults 640/768/1024/1280/1536). Prefer `min-h-dvh` over `100vh` on mobile. Use container queries (`@container`) for component-level responsiveness where a component appears at varied widths. Never disable zoom; keep `viewport` meta with `width=device-width, initial-scale=1`.

## Component idioms

- Compose from primitives (Radix under shadcn) rather than monolithic components; primitives carry the a11y (focus trap, roles, keyboard) for free — don't strip focus rings.
- Extract a component only for true repetition; otherwise keep Tailwind utilities inline.
- Avoid dynamically constructed class strings (`` `text-${color}-500` ``) — Tailwind's purge can't see them; use full class names or a lookup map.
- Forms: pair `react-hook-form` + `zodResolver` + shadcn `Form`/`FormField`/`FormMessage`. Visible labels (not placeholder-only), error below the field, disabled + spinner on async submit, auto-focus the first invalid field.
- Tables: for large data pair shadcn Data Table (TanStack Table) with virtualization, stable column defs, and explicit empty/loading/error states.
- Icons: one set (Lucide by default), consistent stroke width and size tokens; no emoji as structural icons.

## Reviewing UI against the Web Interface Guidelines

For a spec-driven UI/UX review (accessibility, interaction, layout compliance), fetch the current Vercel Web Interface Guidelines and check the target files against them, reporting findings in terse `file:line` form:

```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

Fetch fresh each review (the rules evolve), read the files under review, apply every rule, and output `path:line — issue → fix`. This complements the render → score → refactor loop in `design-quality.md`: guidelines catch spec violations, the loop catches aesthetic and polish gaps.
