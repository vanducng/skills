# TanStack Reference

Use this reference when the app uses or should use TanStack Router, Query, Form, Table, Virtual, or Start.

## Selection

- **Router:** choose for type-safe client-first routing, URL state, loaders, nested routes, and code splitting.
- **Query:** choose for server state: fetch, cache, retry, dedupe, invalidate, refetch, optimistic update.
- **Form:** choose for complex typed forms with sync/async validation and fine control over validation timing.
- **Table:** choose for headless data grids where the app owns markup, design, accessibility, and state.
- **Virtual:** choose when lists/tables are large enough that rendering all rows hurts responsiveness.
- **Start:** choose for full-stack React when the team wants TanStack Router plus SSR, server functions, server routes, middleware, and deployment flexibility.

Do not choose TanStack just because it is available. For small static pages, native React state and simple forms may be enough.

Sources:

- Router: https://tanstack.com/router/latest
- Query: https://tanstack.com/query/latest/docs/framework/react/overview
- Table: https://tanstack.com/table/v8/docs/overview
- Form validation: https://tanstack.com/form/latest/docs/framework/react/guides/validation
- Start: https://tanstack.com/start/latest/docs/framework/react

## Router

Route structure is the app contract.

Rules:

- Do not hand-edit generated route trees.
- Keep route files small: route definition, loader/action hooks, and component.
- Use URL/search params for shareable filters, tabs, sort, pagination, and selected entity.
- Validate search params at the route boundary.
- Use route loaders for data needed to render the route shell.
- Provide pending and error states at route boundaries.
- Test direct URL entry, browser back/forward, search-param changes, and nested route transitions.

File-based routing creates routes from files/directories instead of a hand-coded tree. Use it when it fits the repo convention. Source: https://tanstack.com/router/latest/docs/routing/file-based-routing

## Query

Use Query for server state, not local UI state.

Patterns:

- Query keys must be stable and include all variables that affect the result.
- Keep fetch functions outside components when practical.
- Model freshness deliberately with `staleTime` and `gcTime`.
- Use mutations for server writes and invalidate or update affected queries.
- Use optimistic updates only when rollback is clear.
- Handle loading, background refetch, empty, error, and permission states separately.
- Do not copy query data into component state unless the user is editing a draft.

Checklist:

- Query key includes tenant/user/filters/page/sort where applicable.
- Retry policy does not spam write endpoints or user-visible failures.
- Mutation handles duplicate submit and disabled state.
- Invalidations are targeted, not global cache blasts.
- Errors are visible and recoverable.

Source: https://tanstack.com/query/latest/docs/framework/react/guides/queries

## Form

TanStack Form is headless, so accessibility and layout remain your responsibility.

Rules:

- Keep visible labels and helper/error text in the markup.
- Pick validation timing intentionally: blur or submit by default; change/input only for immediate useful feedback.
- Use sync validators for local invariants and async validators for server-backed checks.
- Debounce async validation and cancel stale requests.
- Keep schema output aligned with backend contracts. Do not silently coerce away backend meaning.
- Preserve values on validation failure.
- Focus the first invalid field after submit.

Source: https://tanstack.com/form/latest/docs/framework/react/guides/validation

## Table

TanStack Table is headless: it provides row/column/sort/filter/pagination state, not UI.

Rules:

- Define columns outside render or memoize them.
- Keep column IDs stable.
- Render semantic table markup unless the design truly requires grid/list markup.
- Implement keyboard-accessible sorting, selection, menus, resize handles, and row actions.
- Pair large datasets with server-side pagination/filtering or virtualization.
- Do not render 10k rows and hope React is fast enough.
- Add loading skeletons with stable row heights.
- Add empty, filtered-empty, error, and permission states.
- Use tabular numbers for numeric data and right-align where appropriate.

Source: https://tanstack.com/table/v8/docs/overview

## Start

TanStack Start is full-stack React built around TanStack Router. Use it when the app needs SSR, server functions, server routes, middleware, and a client-first routing model.

Rules:

- Understand where code runs: server-only, client-only, or isomorphic.
- Use import protection or equivalent checks to prevent server/client boundary leaks.
- Protect the data/API boundary before relying on route UI guards.
- Keep server functions small and validated.
- Use server routes for raw HTTP endpoints, webhooks, file uploads, and auth callbacks.
- Plan hydration and streaming states as part of UX, not as afterthoughts.

Relevant docs:

- Execution model: https://tanstack.com/start/latest/docs/framework/react/guide/execution-model
- Code execution patterns: https://tanstack.com/start/latest/docs/framework/react/guide/code-execution-patterns
- Import protection: https://tanstack.com/start/latest/docs/framework/react/guide/import-protection
- Authentication: https://tanstack.com/start/latest/docs/framework/react/guide/authentication

## Common Failure Modes

- Generated route tree edited by hand.
- Search params are untyped strings everywhere.
- Query keys omit filters or tenant/user identity.
- Mutation succeeds but dependent queries stay stale.
- Forms validate on every keystroke and fight the user.
- Table has mouse-only row actions.
- Virtualized rows have variable height without measurement.
- Start app imports server-only code into client files.
- Auth protects pages but not server functions/routes.

## Verification

Run:

- Typecheck to catch route and query key type drift.
- Unit/component tests for forms, table controls, and URL state.
- E2E tests for direct URL entry, navigation, filter/sort/pagination, mutation success/failure, and permission boundaries.
- Browser check for loading, error, empty, and refetch states.
