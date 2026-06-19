# App Frameworks Reference

Use this reference for React, Next.js, monorepos, app architecture, routing, caching, icons, and design-system integration.

## Framework Selection

Default conservatively:

- **Existing app:** stay on its current framework, router, component system, and package manager unless the user requested migration.
- **Static HTML artifact:** use `vd:opendesign` if the task is a standalone mockup, poster, landing artifact, deck, or single-file HTML design.
- **Full-stack FastAPI + React app:** use `vd:fastreact` when the user asks for a new FastAPI/Python backend plus React frontend.
- **React app needing SSR/RSC/SEO/content:** Next.js App Router is usually the practical default.
- **Client-first typed SPA:** TanStack Router plus Query is often better than Next.js if SSR/SEO is not central.
- **Monorepo:** use Turborepo only when multiple apps/packages benefit from shared tasks and cache. Do not add it for one app.
- **3D/canvas:** load `threejs.md` only when the UI explicitly needs 3D/WebGL/WebGPU/canvas.

## React Boundaries

Keep component boundaries boring:

- Container components fetch or orchestrate data.
- Presentational components accept typed props and stay reusable.
- Forms own validation and submission state close to the fields.
- Server state belongs in a server-state tool, not duplicated in local state.
- Local UI state stays local unless URL state, global state, or persistence is truly needed.
- Context is for cross-cutting concerns; do not use it as a write-heavy store.

Prefer:

- Semantic elements before custom div roles.
- Controlled URL/search params for filters, tabs, pagination, and shareable state.
- Stable keys and memoized heavy column/option definitions.
- Suspense/error boundaries when the framework supports them and the UX benefits.

## Next.js App Router

Current official docs state that layouts and pages are Server Components by default. Use Client Components only when you need:

- State or event handlers.
- Effects or browser lifecycle logic.
- Browser-only APIs such as `window`, `localStorage`, or geolocation.
- Custom hooks that depend on client behavior.

Use Server Components when you need:

- Data close to databases or APIs.
- Secrets/API keys without exposing them to the client.
- Reduced browser JavaScript.
- Progressive streaming and faster first paint.

Rules:

- Put `"use client"` at the smallest interactive leaf possible.
- Never import server-only modules from a client boundary.
- Pass serializable data from Server Components into Client Components.
- Use `children` slots to compose server-rendered content inside client shells when needed.
- Provide `loading.tsx`, `error.tsx`, and not-found handling where routes can wait or fail.
- Keep route segment layouts focused; do not put page-specific state in global layouts.

Sources:

- Next.js Server and Client Components: https://nextjs.org/docs/app/getting-started/server-and-client-components
- React Server Components: https://react.dev/reference/rsc/server-components

## Next.js Caching

As of current Next.js docs, Cache Components are the preferred explicit model when enabled:

```ts
// next.config.ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  cacheComponents: true,
}

export default nextConfig
```

Use:

- `"use cache"` for cacheable pages, components, or functions.
- `cacheLife` for lifetime.
- `cacheTag` / `updateTag` for invalidation.
- Dynamic rendering for request-specific or user-specific data.

Avoid:

- Assuming old implicit fetch caching behavior in new projects.
- Caching authenticated or permission-sensitive data without a clear key and invalidation model.
- Hiding stale-data behavior from the user when freshness matters.

Sources:

- Next.js Caching: https://nextjs.org/docs/app/getting-started/caching
- `cacheComponents`: https://nextjs.org/docs/app/api-reference/config/next-config-js/cacheComponents

## Monorepos And Turborepo

Use Turborepo when there are multiple apps/packages and shared task graphs:

```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "dist/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "test": {
      "dependsOn": ["build"]
    }
  }
}
```

Notes:

- Current Turborepo docs use `tasks`, not older `pipeline` terminology.
- Include all generated output paths or caching will be misleading.
- Add environment inputs (`env`, `globalEnv`) when builds depend on env vars.
- Do not cache watch/dev servers.
- Keep shared packages small and versioned through workspace dependencies.

Source: https://turborepo.dev/docs/reference/configuration

## Component Systems

Use the existing system first:

- shadcn/ui: preserve Radix accessibility contracts and Tailwind token mapping.
- Tailwind: prefer semantic classes and tokens over arbitrary one-off values.
- CSS modules/plain CSS: preserve file organization and naming conventions.
- MUI/Chakra/Mantine/etc.: use their accessible primitives and theming APIs.

When adding components:

- Include loading, empty, error, disabled, hover, focus, active, selected, and destructive states.
- Make variants explicit and typed.
- Keep icon and text spacing stable.
- Do not create nested card shells.
- Avoid hidden layout coupling: component should not require a parent width magic number.

## Icons

- Prefer the app's existing icon library.
- If the app already uses `lucide-react`, use it for tool buttons and common actions.
- Do not mix icon families in the same hierarchy level.
- Icon-only controls require accessible names and tooltips when the icon is not universally obvious.
- Use `currentColor` so icons inherit theme state.

## Integration Checklist

Before shipping:

- Route works on direct load and navigation.
- Browser refresh preserves expected URL state.
- Loading, error, not-found, permission, and empty states render.
- Layout works at mobile and desktop widths.
- Server/client boundaries do not leak secrets or server-only imports.
- Bundle impact is reasonable; heavy modules are split or lazy when possible.
- Tests cover the main user path and the riskiest state transitions.
