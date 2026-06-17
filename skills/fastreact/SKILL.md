---
name: fastreact
description: "Scaffold and build a full-stack web app: FastAPI backend (Python, uv, SQLModel, Postgres, Alembic, JWT + Google OAuth, boto3/S3) + React frontend (Vite, TypeScript, shadcn/ui + Tailwind, TanStack Router/Query/Table, Zod, Axios), wired with Docker Compose. Use this skill whenever the user wants to spin up, bootstrap, create, or design a new full-stack webapp; an API-first backend + SPA frontend; an admin/portal/dashboard app; file upload + S3; RBAC / role-based auth with seeded test users; local docker dev; or asks for a 'FastAPI + React' / 'Python + React' project. Runs mockup-first: marketing-design (brand/logo raster) + opendesign (HTML page mockups) before code, then ports the design to Tailwind/shadcn. Covers project structure, local setup, auth/RBAC, S3 uploads, and the gotchas that break these stacks."
argument-hint: "[app description | scaffold | mockup | backend | frontend]"
license: MIT
metadata:
  author: vanducng
  version: "1.2.0"
---

# fastreact — FastAPI + React full-stack webapp

Build a production-shaped full-stack web app from a mockup to a running Docker Compose stack.
**Backend:** FastAPI, uv, SQLModel, Postgres, Alembic, JWT + Google OAuth, boto3 (S3).
**Frontend:** Vite, React, TypeScript, shadcn/ui + Tailwind, TanStack Router (file-based) / Query / Table, Zod, Axios.
**Infra:** Docker Compose (postgres + backend + frontend), seeded test users, agent-browser E2E.

## When to use
- "Spin up / bootstrap / create a full-stack webapp", "FastAPI + React", "Python backend + React frontend".
- An admin panel, client portal, dashboard, or internal tool with auth + RBAC + file upload + S3.
- API-first backend with a typed SPA; local docker dev with seeded users.

## Scope
This skill handles scaffolding, conventions, and local setup for a FastAPI+React+Postgres+S3 webapp.
It does NOT: deploy to cloud, generate raster brand art itself (delegates to `vd:marketing-design`), or design HTML pages itself (delegates to `vd:opendesign`). For pure UI-token/Tailwind work use `vd:webdesign`. Never put secrets in tracked files; always a gitignored `.env`.

## Workflow (numbered)

### 1. Mockup first (design before code)
Lock the look before writing app code. Save artifacts under the injected `Visuals:` path in a `mockup-{ts}-{app-slug}/` subdir, where `{app-slug}` is a kebab-case name for the app/feature.
1. **Brand/logo (raster):** use `marketing-design` (`design logo` / `create CIP`) for the mark + favicons. Engine: Codex `gpt-image-2` via ChatGPT, falls back to Gemini. To stay faithful to an existing logo, pass it as a reference image (`codex exec -i <ref>` or the cip `--logo`).
2. **HTML page mockups:** use `opendesign` for the screens (login, dashboard, tables, detail) plus an `index.html` gallery and ONE source-of-truth `theme.css` (color tokens, type scale, spacing, components). marketing-design defers HTML/dashboards to opendesign.
3. Get approval on direction (style, screens) with concise preview options before building.
4. Treat the approved `theme.css` + screens as the contract: the frontend MUST match them.
Details: `references/design-mockup-workflow.md`.

### 2. Scaffold the project
Run the scaffolder (idempotent, never overwrites existing files):
```bash
bash scripts/scaffold.sh <project-dir> <app-name>
```
It creates `backend/`, `frontend/`, `docker-compose.yml`, `Makefile`, `.gitignore`, `.env.example`.
Then write the real `.env` (gitignored) with DB + JWT + AWS/S3 + Google OAuth + seed creds.
Structure + conventions: `references/project-structure.md`.

### 3. Build the backend (API-first)
Implement under `backend/app/`: `apis/v1` thin routers, `services` stateless logic, `clients` I/O seams, `models` SQLModel tables, `schemas` Pydantic contracts, `core` config/db/security/exceptions/permissions, `dependencies` DI, `middleware`, `tasks/seed`. One Alembic migration per change. Auth = bcrypt + JWT (HS256) + optional Google OAuth (domain allowlist). S3 = boto3 wrapper in `clients/s3.py`. Verify: `uv sync && uv run python -c "import app.main" && uv run pytest`.
Auth/RBAC/S3 patterns: `references/auth-rbac.md`.

### 4. Build the frontend (feature slices)
`src/app/routes` (TanStack file-based: `_protected` layout, `login`, `403/500`); `src/features/<slice>` (schemas.ts + queries.ts + components/); `src/components/{ui,layout}`; `src/lib` (api-client, query-client, permissions, utils); `src/config/env.ts` (Zod). Port the approved `theme.css` into `src/index.css` + Tailwind tokens (map shadcn HSL vars to the brand palette). Match the mockups exactly. Verify: `npx tsc --noEmit && npm run build`.

### 5. Run locally with Docker Compose
`make up` builds + starts postgres, then backend (migrate + seed on entrypoint), then frontend (nginx). Pick host ports that are free (`lsof -iTCP:<port>`; common conflicts with other local stacks). `make logs`, `make seed`, `make clean` (down -v resets DB). Local setup + entrypoint: `references/local-setup.md`.

### 6. Seed + verify end-to-end
Seed deterministic test users per role. Verify the real flow in the browser via `vd:web-e2e` (scaffold `.e2e/config.json` from its compose-spa example: readyz gate, form login, persistent profile per role) — login → core feature → RBAC — and curl the API (incl. real S3 upload/delete). For frontend layout work, run desktop and mobile viewport checks against the Docker stack and verify no horizontal overflow, hidden action controls, stale bundles, or console errors. The `agent-browser` CLI works as a lighter alternative when traces aren't needed. Loop on fixes until the stack is healthy and the flow passes.

## Reusable assets
- `scripts/scaffold.sh` — generates the project skeleton (run it; do not hand-create dirs).
- `references/project-structure.md` — exact backend + frontend trees + naming conventions.
- `references/local-setup.md` — docker-compose, Dockerfiles, entrypoint, Makefile, ports, seed.
- `references/auth-rbac.md` — JWT + Google OAuth, role model, permission deps, S3 key scheme.
- `references/design-mockup-workflow.md` — marketing-design + opendesign then theme port.
- `references/gotchas.md` — the bugs that recur in this stack. READ before frontend↔backend integration.
- `references/deployment.md` — AWS deploy: EC2+compose, SSM/Ansible, RDS, ALB, ECR, OIDC; security floor + pre-apply checklist.

## Hard rules (this stack bites here; see references/gotchas.md)
1. **FormData uploads:** never set `Content-Type: multipart/form-data` manually; in the axios request interceptor delete the default JSON header when `data instanceof FormData` so the browser sets the boundary. The backend `UploadFile` param name MUST match the FormData key (`files`/`file`).
2. **Zod and the backend contract:** read the backend Pydantic schema before writing the Zod schema. IDs are ints (use `z.coerce.string()` if the UI wants strings); use `nullable()` not `optional()` when the key is always present but may be null. A parse mismatch surfaces as "could not load".
3. **TanStack route nesting:** a `foo.tsx` that has children (`foo.$id.tsx`, `foo.bar.tsx`) MUST be a layout that renders `<Outlet/>`; put the page body in `foo.index.tsx`. Otherwise the child route renders the parent's page.
4. **Brand lockup grid:** if the wordmark stacks under the icon via CSS grid, the `.wm` wrapper needs `display:contents` so the `<b>`/`<span>` become grid items, else the tagline renders inline.
5. **Ports:** other local stacks squat 5173/5432/8000/8080; pick free host ports in compose and set CORS + `VITE_API_BASE_URL` to match the chosen frontend origin/backend port.
6. **Secrets:** `.env` is gitignored; scan staged files for key patterns (`AKIA…`, `GOCSPX-`) before any push.
7. **Tables and search:** every table needs loading, empty, filtered-empty, and error states, plus a body frame that keeps pagination pinned. Client-side search is only acceptable when the full result set is loaded and small; otherwise add backend `q`, filter, sort, limit, and offset params.
8. **Admin filters:** use a compact toolbar with search plus select/dropdown filters for role, company, status, and action. Avoid long flat pill rows that wrap badly on mobile.
9. **Avatar consistency:** expose `avatar_url` from auth/user schemas when available, capture Google `picture`, and render one shared Avatar primitive everywhere (topbar, profile, user tables, audit rows). Fallback initials must use one deterministic color function.
10. **Responsive verification:** after login, table, profile, or shell changes, run local browser E2E in desktop and mobile widths before shipping. Check screenshots, not just typecheck/build.
