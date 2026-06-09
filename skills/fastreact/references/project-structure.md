# Project structure & conventions

Two apps in one repo, composed by `docker-compose.yml` at the root.

```
<app>/
├── docker-compose.yml      postgres + backend + frontend
├── Makefile                up/down/clean/logs/seed/migrate
├── .env                    gitignored — DB, JWT, AWS/S3, Google OAuth, seed creds
├── .env.example            committed template (no secrets)
├── .gitignore              .env, **/node_modules, **/dist, **/.venv, pgdata/
├── backend/
│   ├── app/
│   │   ├── apis/v1/        thin FastAPI routers: health, auth, files, <resources>, audit
│   │   ├── services/       stateless business logic (CRUD); the SERVICE owns commit()
│   │   ├── clients/        I/O seams: s3.py (boto3), google_oauth.py (httpx)
│   │   ├── models/         SQLModel tables; base.py audit-col factories (created_at/updated_at/
│   │   │                   created_by/updated_by/deleted_at) — standardize across domain tables; __init__ imports all
│   │   ├── schemas/        Pydantic request/response (from_attributes=True)
│   │   ├── core/           configs (pydantic-settings), db (async engine+session), security
│   │   │                   (bcrypt+JWT), exceptions, permissions (roles)
│   │   ├── dependencies/   FastAPI DI: db.py (Session), auth.py (CurrentUser, role gates)
│   │   ├── middleware/     cors, request_id, error_handler
│   │   ├── tasks/          seed.py (idempotent), background loops if needed
│   │   └── main.py         create_app(): cors + middleware + handlers + api_router; lifespan
│   ├── migrations/         Alembic (env.py async, versions/0001_init.py hand-written)
│   ├── tests/              pytest (aiosqlite in-memory + dependency_overrides)
│   ├── pyproject.toml      uv deps; [tool.ruff] line-length 120; pytest asyncio_mode=auto
│   ├── alembic.ini
│   ├── entrypoint.sh       alembic upgrade head; seed if SEED_ON_START=1; uvicorn
│   └── Dockerfile.app      uv builder (ghcr.io/astral-sh/uv:python3.12) -> python:3.12-slim, non-root
└── frontend/
    ├── src/
    │   ├── app/routes/     TanStack file-based: __root, login, _protected(.tsx layout),
    │   │                   _protected/{index,<feature>,<feature>.$id}, 403, 500
    │   ├── features/       vertical slices: <slice>/{schemas.ts, queries.ts, components/}
    │   │   └── shared/components/data-table.tsx   reusable paginated TanStack Table
    │   ├── components/
    │   │   ├── ui/         hand-written shadcn primitives (Radix + cva + cn)
    │   │   └── layout/     app-shell, app-sidebar (collapse rail), top-bar, brand
    │   ├── lib/            api-client (axios+interceptors), query-client, permissions,
    │   │                   route-guards, theme, timezone, utils (cn)
    │   ├── config/env.ts   Zod-validated import.meta.env (VITE_API_BASE_URL)
    │   ├── index.css       Tailwind + ported brand theme tokens (shadcn HSL vars)
    │   └── main.tsx        createRouter + RouterProvider
    ├── package.json        scripts: dev / build (tsc -b && vite build) / preview / lint
    ├── vite.config.ts      tanstackRouter plugin + react + @ alias + /api proxy
    ├── tailwind.config.js, postcss.config.js, components.json, tsconfig*.json
    ├── nginx.conf          SPA try_files -> /index.html; /api/ -> backend:8000
    └── Dockerfile          multi-stage: node build (npm ci && npm run build) -> nginx
```

## Naming conventions
- Files: kebab-case, descriptive (a reader knows the purpose from the name).
- Backend: `models/` = SQLModel `table=True`; `schemas/` = Pydantic (no envelope, return bare models; errors `{"detail": str}`). Router prefixes plural lowercase (`/files`, `/users`). Service methods = async static methods. Keep files focused.
- Frontend: import a feature only via its `index.ts` barrel; no feature→feature imports (shared layer only). Query keys: `<thing>Keys = { all, list(), detail(id) }`.
- One Alembic migration per schema change; hand-write `0001_init.py` to match models (don't rely on autogenerate for the first one).

## Reference implementation
The CNB Hire Intelligence build (github.com/careernowbrands/cnb-hire-intelligence) is the canonical example of this structure: file-upload portal, RBAC (cnb_admin/cnb_data/cnb_ae/client_admin), S3, audit log, profile, admin tables.
