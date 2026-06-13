# Gotchas — bugs that recur in this stack

Read this BEFORE wiring the frontend to the backend. Each cost a debug loop in the reference build.

## Frontend ↔ backend integration

### 1. Multipart upload returns 422
Two independent causes, often together:
- The frontend appended a different field name than the backend expects (`form.append('files', f)` vs FastAPI `file: UploadFile`). Make them match (prefer `files: list[UploadFile]` + `form.append('files', f)`).
- A manual `Content-Type: multipart/form-data` header (with no boundary) breaks parsing. **Never set it.** Worse: a GLOBAL axios default `Content-Type: application/json` also suppresses the auto boundary. Fix in the request interceptor: `if (config.data instanceof FormData) delete config.headers['Content-Type']`.

### 2. "Could not load" — Zod parse rejects a valid 200
The frontend Zod schema drifted from the backend Pydantic shape. Symptoms: raw `fetch` works, the app errors. Always read `backend/app/schemas/*.py` first, then:
- IDs are ints from the DB. Use `z.coerce.string()` if the UI treats id as string.
- A field that's always present but can be null → `z.string().nullable()`, NOT `.optional()` (optional adds `undefined` and breaks consumers).
- Enum values must match exactly (e.g. audit actions are `upload`/`download` present-tense, not `uploaded`).
- Field names must match (`ip` not `ip_address`, `actor_email` not `actor_name`).

### 3. TanStack Router: a child route renders the parent's page
`foo.tsx` + `foo.$id.tsx` (or `foo.bar.tsx`) makes `foo` the LAYOUT for its children. If `foo.tsx` renders a page (no `<Outlet/>`), `/foo/123` shows `foo`'s page, not the child. Fix: make `foo.tsx` a layout (`component: () => <Outlet/>` + any guard) and move the list/page body to `foo.index.tsx`. Then regenerate the route tree (the vite plugin does it on `npm run dev`/`build`; if `tsc -b` runs first and fails on new route paths, run the dev server briefly to regenerate `route-tree.gen.ts`).

### 4. Brand lockup tagline renders inline
A grid lockup that places `<b>` (name) on row 1 and `<span>` (tagline) on row 2 only works if their wrapper has `display: contents` (so they become grid items of `.brand`). Without it the wrapper is one grid cell and name+tagline sit inline. The icon should span both rows (`grid-row: 1 / 3; align-self:center`) to center against the two lines.

## Local / docker

### 5. Port conflicts on `docker compose up`
Other local stacks squat 5173 / 5432–5435 / 8000 / 8080 (`Bind for :::PORT failed: port is already allocated`). Check free ports first, then set the compose host ports + `VITE_API_BASE_URL` + `CORS_ORIGINS` to agree. Backend is reached by the browser on its published port, so CORS must list the actual frontend origin.

### 6. Stale image / stale bundle
Backend code is baked in — rebuild the image to pick up changes (`docker compose up -d --build backend`). Frontend asset hashes change per build; a cached browser context can run old JS — hard-reload or use a fresh context. Reset the DB to re-seed: `docker compose down -v`.

### 7. `uv sync --frozen` needs a lock
Use `uv sync --no-dev` (no `--frozen`) in the Dockerfile so it resolves without a committed `uv.lock`, or commit the lock. Pin `.python-version` to match the image (uv may default to a newer Python locally than the 3.12 image).

## Verification

### 8. agent-browser daemon quirks
Screenshots via the agent-browser daemon may fail in some envs; DOM-text checks (`get url`, `snapshot`, `eval document.body.innerText`) are reliable. For visual checks (logo, layout), drive the app with Playwright or Puppeteer and screenshot it. Refs from a snapshot go stale after navigation — re-snapshot before interacting.

### 9. File-upload via headless browser
The visible "Choose files" button hides the real `<input type=file>`; target the input directly: `agent-browser upload "input[type=file]" <path>`. Verify the result against the backend (the DB/S3), not just the toast.

## Security

### 10. Never commit secrets
`.env` (AWS keys, OAuth secrets) must be gitignored. Before any push, scan staged/source files for `AKIA[0-9A-Z]{16}`, `GOCSPX-`, and known secret values. Hooks may block grep commands containing `node_modules`/`dist`/`build` tokens — scope greps to source dirs.

## Design & scope discipline (mined from build reviews)
These recurred across the reference build's review rounds. They're skill-scoped design defaults (rule-miner correctly rejected them as *global* rules; apply them here, not everywhere).

### 11. Default to minimal, consistent, data-focused UI
Prioritize content over decoration. Do NOT add, unless explicitly asked: oversized icons (clamp stat-card icons ~16px in a ~30px badge; trend arrows ≤14px), decorative cards, drag-drop zones (a single Upload button is enough), a global top search bar, a notifications bell, or security/encryption boilerplate copy in the product chrome (keep that in a Help/Learn-more page). Drop metadata clutter (e.g. message-count suffixes). Truncate overflowing labels to their control. Keep buttons mockup-sized (e.g. h-9, not h-12). When a table has more than a couple of action filters, use a select/dropdown instead of a flat pill row that wraps badly.

### 12. Don't frame one feature as the whole product
Copy and IA should stay extensible (e.g. "your workspace for hire data, starting with uploads" — not "the upload portal"). A first feature is the first of many.

### 13. Build only what's asked (YAGNI)
No pages/sites/docs the user didn't request. Route a docs site straight to the docs (no separate marketing landing). Don't auto-generate redundant docs that duplicate code/state and go stale.

### 14. Zero em-dashes, swept before commit
No em-dash (—) anywhere — UI copy, placeholders, comments, generated text. Use a comma or rephrase. Sweep `grep -rn "—" src` and remove leftovers before committing; treat a stray em-dash as a bug.

### 15. Every modal needs a visible close button
The shadcn `DialogContent` must render the top-right `DialogPrimitive.Close` (X). Put it in `components/ui/dialog.tsx` once so every dialog (upload, confirm, etc.) inherits it; don't rely on click-outside/Esc alone.

### 16. Tables should hold their shape with few rows
Give the `DataTable` body a consistent min-height (e.g. `min-h-[420px]`, ~ pageSize rows) and keep the pagination footer pinned below. A 1-row table that collapses to a stub looks broken; a fixed frame reads as a real table. (Common, tasteful; not a scroll hack.) Design all states: loading skeleton, empty database, filtered-empty, and error. Filtered-empty should show a compact message and a clear/reset action instead of a lonely "No rows" string floating in a huge frame.

### 17. Login footer + single version constant
Add a centered login footer `© <Brand> · v<APP_VERSION>` and reuse the SAME `APP_VERSION` (one `src/config/version.ts`) in the sidebar status chip. The brand lockup should be a link to `/` (home).

### 18. Client-facing copy: precise, not over-claiming, not over-specifying
For tenant/client UI + docs: describe what users actually do (e.g. "upload hire data exported from your ATS"), not internal jargon (no "leads/rosters/applicants", no "lead database"). Don't over-claim outcomes ("real hires", not "potential"; no "never sold/shared" promises). Don't leak infra specifics (say "in CNB's AWS (S3)", not the bucket name or "organized by your company identifier"). Keep internal role tables / audit details OUT of client docs.

### 19. Standardize audit columns + soft delete
Give domain tables a consistent audit shape via base.py col factories: `created_at`, `updated_at`, `created_by`, `updated_by` (FK users, SET NULL), and `deleted_at` for soft-deletable entities. Populate `created_by`/`updated_by` from the acting user in services. Soft delete = set `deleted_at`; the service `list()`/`get()` MUST filter `deleted_at IS NULL`. Reserve HARD delete for rows that own an external resource (e.g. an S3 object) where a tombstone would lie. Immutable logs (audit) keep only `created_at`. Add columns via a migration; backfill nothing.

### 20. Internal "support workspace" + tenant scoping
Internal (provider) users often need BOTH an Admin section AND the tenant Workspace, seeing ALL tenants' data (e.g. all client files with a Company column + filter) to support them. Implement scoping in the service (`is_internal(role)` → all rows; tenant user → own `company_id`), gate write actions by role (e.g. AE = view+download, not delete), and render a Company column only for internal users. Route internal users' home to the admin landing.

## Deployment (AWS)

### 21. postgres:18+ moved its data dir
The 18+ image wants the volume at `/var/lib/postgresql` (NOT `/data`); the old mount → "unused mount/volume", container exits 1. Fix: `pgdata:/var/lib/postgresql` (or set `PGDATA=/var/lib/postgresql/data` to keep the old layout). Bumping the PG MAJOR also needs a volume wipe (`down -v`); data dirs aren't cross-major compatible.

### 22. RDS minor versions get removed
A pinned minor (e.g. `16.4`) fails at terraform APPLY, not plan/validate. Verify first: `aws rds describe-db-engine-versions --engine postgres` + `describe-orderable-db-instance-options --db-instance-class <class>`.

### 23. ECR IMMUTABLE is a silent no-op through a shared module
A `for_each` module that doesn't pass `image_tag_mutability` creates the repo MUTABLE regardless of your locals. Verify the module wires the var. Separately: IMMUTABLE + a moving tag (`:prod`/`:latest`) breaks on the 2nd push (`ImageTagAlreadyExistsException`) → deploy by git SHA only.

### 24. Internet-facing ALB needs >=2 AZs
A single-AZ VPC needs a Terraform-created 2nd-AZ subnet pair (the compute target can stay single-AZ).

### 25. 443-only egress breaks DNS
Tightening app egress to 443 also blocks resolution. Allow 53 (udp+tcp) to the VPC resolver CIDR, and 5432 to the RDS SG.

### 26. Terraform repo hygiene
Gitignore `.terraform/` and `*.tfstate*` but KEEP `.terraform.lock.hcl`; run `terraform providers lock -platform=linux_amd64 -platform=darwin_arm64` so linux CI has provider hashes.

### 27. Pin local Postgres to the RDS MAJOR
Pin docker-compose Postgres to the SAME MAJOR as the RDS engine (real drift caught: local 16 vs prod 18).

### 28. Automate ACM + DNS when the zone is in-account
If the Route53 zone is in the same AWS account, create the ACM validation records + `aws_acm_certificate_validation` + the app alias record in Terraform. No manual CNAME handoff.

### 29. RDS param-group family must match the engine MAJOR
Pinning `family = "postgres16"` with an 18 engine fails at APPLY (InvalidParameterCombination), not validate/plan. Derive it: `family = "postgres${split(".", var.db_engine_version)[0]}"` so it tracks the version.

### 30. AWS SSM names/descriptions reject `+` and math symbols
SSM patch-baseline (and similar) fields allow `\p{P}` punctuation but NOT `\p{S}` symbols, so a `+` in a description fails apply with a regex ValidationException. Use plain words/commas.

## Later portal UI corrections

### 31. Client-side table search only searches loaded rows
If the API returns only the first page or a capped recent window, frontend search will silently miss valid records. Use client-side search only when the full result set is already loaded and small. For audit logs, files, users, or anything expected to grow, add backend query params (`q`, filters, sort, limit, offset) and include the active filter state in the query key.

### 32. Avatar/photo display must be shared
Google OAuth often provides a profile photo, but pages drift if each table/menu renders its own initials badge. Capture `picture` as `avatar_url` in the backend user model/schema, then use one frontend Avatar primitive everywhere: topbar, profile, user tables, audit rows, and menus. If no image exists, use the same initials and deterministic color helper in all locations.

### 33. Profile pages should be useful, not tall side rails
Profile/account screens are utility surfaces. Keep identity, editable display settings, theme, and recent activity balanced in a constrained layout. Cap recent activity and link to the audit view for long history. Do not let an uncapped activity feed stretch one column far past the rest of the page.

### 34. Sticky elements must be tested in the real scroll container
Many SPA shells scroll inside `<main>`, not `window`. `position: sticky` is relative to that scroll container, so a TOC or right rail can sit too low after scroll if the offset is guessed from the viewport. Test initial and scrolled positions in the running app, including dark mode if supported.

### 35. Mobile E2E is part of frontend done
Desktop screenshots can hide broken mobile filters, oversized login cards, clipped table actions, and horizontal overflow. After shell, login, table, profile, or sticky-layout changes, run browser checks at a mobile viewport and a desktop viewport against the Docker stack. Verify the logged-in route, not just a static mockup.
