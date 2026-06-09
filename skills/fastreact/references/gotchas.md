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
Screenshots via the agent-browser daemon may fail in some envs; DOM-text checks (`get url`, `snapshot`, `eval document.body.innerText`) are reliable. For visual checks (logo, layout) drive the app with Puppeteer (via the chrome-devtools node_modules) and screenshot. Refs from a snapshot go stale after navigation — re-snapshot before interacting.

### 9. File-upload via headless browser
The visible "Choose files" button hides the real `<input type=file>`; target the input directly: `agent-browser upload "input[type=file]" <path>`. Verify the result against the backend (the DB/S3), not just the toast.

## Security

### 10. Never commit secrets
`.env` (AWS keys, OAuth secrets) must be gitignored. Before any push, scan staged/source files for `AKIA[0-9A-Z]{16}`, `GOCSPX-`, and known secret values. Hooks may block grep commands containing `node_modules`/`dist`/`build` tokens — scope greps to source dirs.

## Design & scope discipline (mined from build reviews)
These recurred across the reference build's review rounds. They're skill-scoped design defaults (rule-miner correctly rejected them as *global* rules; apply them here, not everywhere).

### 11. Default to minimal, consistent, data-focused UI
Prioritize content over decoration. Do NOT add, unless explicitly asked: oversized icons (clamp stat-card icons ~16px in a ~30px badge; trend arrows ≤14px), decorative cards, drag-drop zones (a single Upload button is enough), a global top search bar, a notifications bell, or security/encryption boilerplate copy in the product chrome (keep that in a Help/Learn-more page). Drop metadata clutter (e.g. message-count suffixes). Truncate overflowing labels to their control. Keep buttons mockup-sized (e.g. h-9, not h-12).

### 12. Don't frame one feature as the whole product
Copy and IA should stay extensible (e.g. "your workspace for hire data, starting with uploads" — not "the upload portal"). A first feature is the first of many.

### 13. Build only what's asked (YAGNI)
No pages/sites/docs the user didn't request. Route a docs site straight to the docs (no separate marketing landing). Don't auto-generate redundant docs that duplicate code/state and go stale.

### 14. Zero em-dashes, swept before commit
No em-dash (—) anywhere — UI copy, placeholders, comments, generated text. Use a comma or rephrase. Sweep `grep -rn "—" src` and remove leftovers before committing; treat a stray em-dash as a bug.
