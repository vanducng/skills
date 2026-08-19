# Generate flows by discovery

Bootstrap a project's e2e surface the way a user walks the app. Output is the existing contract: `.e2e/config.json` plus agent-executable `.e2e/flows/<name>.md` files. Do not invent a second schema. Match `references/flows-and-reports.md` for flow files and `references/examples/*.config.json` for config.

This is generation for the next agent, not a QA essay. A generated flow that never ran is a guess.

## When to run

- The repo has no `.e2e/config.json`.
- Config exists (or a feature map exists) but `.e2e/flows/` is empty or missing the features the map names.

Do not regenerate a working surface because the files look thin. Start with exactly one `smoke.md`; add more only when a second real feature is confirmed.

## Discovery pass

1. **Boot** with existing conventions. Prefer the repo's documented `make up` / compose / Herd site. If you write `boot.up` / `boot.down`, they must be detaching commands. Foreground servers are unsupported. Then `node "$E2E" status --wait --json` until health is green. Embedded-SPA gotcha: a 200 proves the container, not the current frontend - rebuild and confirm asset hash / `<title>` after UI changes.
2. **Attach** only via `profile-attach.sh <profile>` (env-sanitized CDP connect + UA check). Never `--profile` mode. Drive with `agent-browser open`, `snapshot -i`, `fill`, `click`, `press Enter`, `get url`. Do not trust `wait --url` on SPA/Inertia navigations.
3. **Walk the running UI** like a user: nav links, routes, forms, logged-out vs logged-in shells. Enumerate user-visible features only.
4. **Confirm the route list** from router/nav source (Laravel routes, TanStack/React Router, Next app dir). The UI walk finds what a user can reach; the source list catches hidden but shipped routes. Prefer the intersection.

Auth: follow `references/auth-strategies.md`. `form` and `token-inject` are scriptable; `oauth-interactive` means you open the profile and ask the human to log in once. Never put real credentials in config. Seeding/reset is per-flow, never auto-run from `boot.up`.

## Propose a feature map

Stop and show a table. Human confirms before any file is written.

| Feature | Route | Preconditions | Success signal |
|---|---|---|---|
| smoke | `/dashboard` | status READY, auth logged-in | authed shell, not a login form |
| create-order | `/orders/new` | seeded catalog, queue worker | toast + row on `/orders` |

- Feature: user-visible name, kebab-case file stem later (`create-order.md`).
- Route: path under `baseUrl`, not an internal API.
- Preconditions: auth strategy, seed data, `checks[]` processes (queue worker).
- Success signal: smallest observable from the user's side (URL, heading, toast, row). Not "200 from `/api`".

Drop admin-only internals, destructive one-shots, and third-party walls you cannot mock. Aim for smoke plus the top 3-5 confirmed features.

## Generate (existing format only)

Layout:

```
<repo>/.e2e/
├── config.json
└── flows/
    ├── smoke.md
    └── <feature>.md
```

**`config.json`** - only non-derivable facts. Copy the closest example and edit:

- `laravel-herd.config.json` - Herd, OAuth, `insecureTLS`, optional `checks[]`
- `compose-spa.config.json` - `boot.up`/`down`, readyz + UI health, `form` auth
- `worktree-portable.config.json` - `${PORT}` / `${WORKTREE_NAME}`

Required shape: `name`, `baseUrl`, `profile`, optional `insecureTLS`, optional `boot.{up,down}`, `health[]` (`url`, optional `expect`, `bodyContains`; GET-only; do not follow redirects), optional `checks[]` (`name`, `cmd`), `auth` (`strategy`, `probeUrl`, `loginUrlPattern`, plus per-strategy fields from auth-strategies). No secrets. `credentials.source` is `gopass`, `env`, or `inline` only for README-public seed users.

**Each flow** is prose markdown, not a DSL. Exact headings from `flows-and-reports.md`:

```markdown
# Flow: create-order

Goal: signed-in user submits an order and sees it listed.

Preconditions:
- `e2e.cjs status` READY and auth logged-in (or injected).
- Queue worker up (`checks[]`); catalog seeded.

Steps:
1. Open <baseUrl>/orders/new.
2. Snapshot; fill the form; press Enter (fill never submits).
3. `get url` is /orders; snapshot shows the new row.

Assertions:
- Final URL is the list route, not a login route.
- Trace run has zero console exceptions.
- No failed first-party requests in the trace.

Notes:
- Skip live payment; mock or stop before the vendor call.
```

Smallest assertion that proves the feature from the user's side. Optional `<name>.batch` only after the `.md` has been driven live, with CSS/`find role|text|label|testid` locators, never `@e` refs.

## Prove

Run at least one generated flow live before claiming the surface exists:

1. `node "$E2E" status --wait --json`
2. Attach, start `vd:browser-trace` capture on the profile port
3. Execute the flow steps with agent-browser
4. `stop-capture` → `bisect-cdp` → `query errors` / `query hosts` (same run-id, that order)
5. Verdict per `flows-and-reports.md` (`PASS` or `FAIL - <symptom>`, absolute evidence paths)

Fix what fails, then re-run that one flow. Cleanup must not delete evidence.

## Maintenance loop

When a flow fails against a changed UI, re-discover **that** feature (route + snapshot + source) and regenerate **that** `.md` (and its `.batch` if present). Never wipe `.e2e/flows/` and regenerate the whole surface blind. Keep the feature map table in the report or a short note next to the flows so the next agent knows what was confirmed.

Adapted from cursor/plugins pstack create-verification-skill (MIT).
