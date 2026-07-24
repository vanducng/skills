#!/usr/bin/env bash
# fastreact scaffolder - lay down a FastAPI + React + Postgres + S3 skeleton.
# Idempotent: only writes files that don't already exist. Produces a runnable
# health backend + a building frontend shell; fill domain code per the skill references.
#   usage: bash scaffold.sh <project-dir> <app-name>
set -euo pipefail
DIR="${1:?usage: scaffold.sh <project-dir> <app-name>}"
APP="${2:?usage: scaffold.sh <project-dir> <app-name>}"
SLUG="$(printf '%s' "$APP" | tr '[:upper:] ' '[:lower:]-')"

w() { # w <path> ; reads file body from stdin; skips if exists
  local p="$DIR/$1"
  mkdir -p "$(dirname "$p")"
  if [ -e "$p" ]; then echo "skip  $1"; cat >/dev/null; else cat >"$p"; echo "write $1"; fi
}

mkdir -p "$DIR"/backend/app/{apis/v1,services,clients,models,schemas,core,dependencies,middleware,tasks}
mkdir -p "$DIR"/backend/migrations/versions "$DIR"/backend/tests
mkdir -p "$DIR"/frontend/src/{app/routes,features/shared/components,components/ui,components/layout,lib,config}
: > "$DIR/backend/migrations/versions/.gitkeep"; : > "$DIR/backend/tests/.gitkeep"

# ---------- root ----------
w .gitignore <<'EOF'
.env
.env.*
!.env.example
**/.env
**/__pycache__/
*.pyc
**/.venv
**/.ruff_cache
**/.pytest_cache
**/node_modules
**/dist
*.tsbuildinfo
pgdata/
.DS_Store
EOF

w .env.example <<EOF
APP_ENV=dev
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=${SLUG}_user
POSTGRES_PASSWORD=change-me
POSTGRES_DB=${SLUG}
SECRET_KEY=change-me
JWT_SECRET=change-me
JWT_EXPIRY_HOURS=8
CORS_ORIGINS=http://localhost:5173,http://localhost:8080
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
GOOGLE_ALLOWED_DOMAIN=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
S3_BUCKET=
S3_PREFIX=${SLUG}
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me
SEED_ON_START=1
VITE_API_BASE_URL=http://localhost:8000/api/v1
EOF

w docker-compose.yml <<'EOF'
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 10
    volumes: [pgdata:/var/lib/postgresql/data]
    ports: ["5436:5432"]
  backend:
    build: { context: ./backend, dockerfile: Dockerfile.app }
    env_file: .env
    environment: { POSTGRES_HOST: postgres, POSTGRES_PORT: 5432 }
    depends_on: { postgres: { condition: service_healthy } }
    ports: ["8000:8000"]
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request;urllib.request.urlopen('http://localhost:8000/api/v1/livez')"]
      interval: 10s
      timeout: 5s
      retries: 12
  frontend:
    build:
      context: ./frontend
      args: { VITE_API_BASE_URL: ${VITE_API_BASE_URL:-http://localhost:8000/api/v1} }
    ports: ["8082:80"]
    depends_on: { backend: { condition: service_healthy } }
volumes: { pgdata: {} }
EOF

w Makefile <<'EOF'
.PHONY: up down clean logs ps seed migrate be-test fe-test
up:; docker compose up -d --build
down:; docker compose down
clean:; docker compose down -v
logs:; docker compose logs -f --tail=120
ps:; docker compose ps
seed:; docker compose exec backend python -m app.tasks.seed
migrate:; docker compose exec backend alembic upgrade head
be-test:; cd backend && uv run pytest
fe-test:; cd frontend && npm run test --silent || true
EOF

# ---------- backend ----------
w backend/.python-version <<'EOF'
3.12
EOF

w backend/pyproject.toml <<EOF
[project]
name = "${SLUG}-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115", "uvicorn[standard]>=0.32", "sqlmodel>=0.0.21",
  "sqlalchemy[asyncio]>=2", "asyncpg>=0.30", "psycopg2-binary>=2.9",
  "alembic>=1.14", "pydantic-settings>=2.6", "pydantic>=2.9",
  "pyjwt>=2.8", "bcrypt>=4.1", "boto3>=1.34", "python-multipart>=0.0.9",
  "httpx>=0.28", "openpyxl>=3.1",
]
[dependency-groups]
dev = ["ruff>=0.8", "pytest>=8.3", "pytest-asyncio>=0.24", "aiosqlite>=0.20", "httpx>=0.28"]
[tool.ruff]
line-length = 120
target-version = "py312"
[tool.ruff.lint]
select = ["E","W","F","I","B","C4","UP"]
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
EOF

w backend/alembic.ini <<'EOF'
[alembic]
script_location = migrations
EOF

w backend/entrypoint.sh <<'EOF'
#!/usr/bin/env sh
set -e
[ "$RUN_MIGRATIONS" != "0" ] && alembic upgrade head
[ "$SEED_ON_START" = "1" ] && (python -m app.tasks.seed || true)
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
EOF

w backend/Dockerfile.app <<'EOF'
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev
FROM python:3.12-slim AS api
RUN useradd --create-home --shell /bin/sh appuser
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app app
COPY migrations migrations
COPY alembic.ini entrypoint.sh ./
ENV PATH=/app/.venv/bin:$PATH PYTHONPATH=/app
RUN chmod +x entrypoint.sh
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD ["python","-c","import urllib.request;urllib.request.urlopen('http://localhost:8000/api/v1/livez')"]
ENTRYPOINT ["./entrypoint.sh"]
EOF

w backend/app/__init__.py <<'EOF'
EOF

w backend/app/core/configs.py <<'EOF'
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "dev"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "app"
    secret_key: str = ""
    jwt_secret: str = "dev-secret-change-me"
    jwt_expiry_hours: int = 8
    cors_origins: str = "http://localhost:5173"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket: str = ""
    s3_prefix: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""
    google_allowed_domain: str = ""
    admin_email: str = ""
    admin_password: str = ""

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def database_url_sync(self) -> str:
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
EOF

w backend/app/core/db.py <<'EOF'
from collections.abc import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.configs import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as s:
        try:
            yield s
        except Exception:
            await s.rollback()
            raise
EOF

w backend/app/main.py <<EOF
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.core.configs import settings


def create_app() -> FastAPI:
    app = FastAPI(title="${APP} API")
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_list,
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )
    # TODO: app.include_router(api_router) once apis/v1 routers exist (see skill references)

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    @app.get("/api/v1/livez")
    async def livez() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/api/v1/readyz")
    async def readyz() -> JSONResponse:
        from app.core.db import AsyncSessionLocal
        try:
            async with AsyncSessionLocal() as s:
                await asyncio.wait_for(s.execute(text("SELECT 1")), timeout=2.0)
            return JSONResponse({"status": "ready"})
        except Exception:
            return JSONResponse({"status": "unavailable"}, status_code=503)

    return app


app = create_app()
EOF

w backend/app/tasks/__init__.py <<'EOF'
EOF
w backend/app/tasks/seed.py <<'EOF'
"""Idempotent seed. Fill in companies/users per the skill's auth-rbac reference."""
def main() -> None:
    print("[seed] TODO: create companies + users (see fastreact/references/auth-rbac.md)")
if __name__ == "__main__":
    main()
EOF
for d in apis apis/v1 services clients models schemas core dependencies middleware; do : > "$DIR/backend/app/$d/__init__.py" 2>/dev/null || true; done

w backend/migrations/env.py <<'EOF'
import asyncio
from logging.config import fileConfig
from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel
from app.core.configs import settings
import app.models  # noqa: F401  (import models so metadata registers)

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url_sync)
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = SQLModel.metadata


def do_run(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async():
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = settings.database_url
    eng = async_engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with eng.connect() as c:
        await c.run_sync(do_run)
    await eng.dispose()


if context.is_offline_mode():
    context.configure(url=settings.database_url_sync, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_async())
EOF

w backend/migrations/script.py.mako <<'EOF'
"""${message}
Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

def upgrade() -> None:
    ${upgrades if upgrades else "pass"}

def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
EOF

w backend/app/models/__init__.py <<'EOF'
# Import every model module here so Alembic sees them on SQLModel.metadata.
EOF

# ---------- frontend ----------
w frontend/package.json <<EOF
{
  "name": "${SLUG}-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint . || true"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.59.0",
    "@tanstack/react-router": "^1.58.0",
    "@tanstack/react-table": "^8.20.0",
    "axios": "^1.7.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "lucide-react": "^0.450.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "sonner": "^1.5.0",
    "tailwind-merge": "^2.5.0",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "@tanstack/router-plugin": "^1.58.0",
    "@types/node": "^22.0.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.6.0",
    "vite": "^5.4.0"
  }
}
EOF

w frontend/vite.config.ts <<'EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
const __dirname = dirname(fileURLToPath(import.meta.url))
export default defineConfig({
  plugins: [
    tanstackRouter({ target: 'react', routesDirectory: 'src/app/routes', generatedRouteTree: 'src/route-tree.gen.ts', autoCodeSplitting: true }),
    react(),
  ],
  resolve: { alias: { '@': resolve(__dirname, 'src') } },
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000' } },
})
EOF

w frontend/tsconfig.json <<'EOF'
{
  "compilerOptions": {
    "target": "ES2022", "lib": ["ES2022","DOM","DOM.Iterable"], "module": "ESNext",
    "moduleResolution": "bundler", "jsx": "react-jsx", "strict": true, "noEmit": true,
    "skipLibCheck": true, "resolveJsonModule": true, "verbatimModuleSyntax": true,
    "baseUrl": ".", "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src"]
}
EOF

w frontend/tsconfig.node.json <<'EOF'
{ "compilerOptions": { "composite": true, "module": "ESNext", "moduleResolution": "bundler", "skipLibCheck": true }, "include": ["vite.config.ts"] }
EOF

w frontend/postcss.config.js <<'EOF'
export default { plugins: { tailwindcss: {}, autoprefixer: {} } }
EOF

w frontend/tailwind.config.js <<'EOF'
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: 'hsl(var(--background))', foreground: 'hsl(var(--foreground))',
        primary: { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
        border: 'hsl(var(--border))', accent: 'hsl(var(--accent))', card: 'hsl(var(--card))',
      },
      borderRadius: { lg: 'var(--radius)', md: 'calc(var(--radius) - 2px)', sm: 'calc(var(--radius) - 4px)' },
    },
  },
  plugins: [],
}
EOF

w frontend/components.json <<'EOF'
{ "style": "default", "tailwind": { "config": "tailwind.config.js", "css": "src/index.css", "baseColor": "neutral", "cssVariables": true }, "aliases": { "components": "@/components", "utils": "@/lib/utils" } }
EOF

w frontend/index.html <<EOF
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${APP}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
EOF

w frontend/nginx.conf <<'EOF'
server {
  listen 80;
  root /usr/share/nginx/html;
  index index.html;
  location /api/ { proxy_pass http://backend:8000; }
  location / { try_files $uri $uri/ /index.html; }
}
EOF

w frontend/Dockerfile <<'EOF'
FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build
FROM nginx:alpine AS serve
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
EOF

w frontend/src/vite-env.d.ts <<'EOF'
/// <reference types="vite/client" />
EOF

w frontend/src/config/env.ts <<'EOF'
import { z } from 'zod'
const schema = z.object({ VITE_API_BASE_URL: z.string().url().default('http://localhost:8000/api/v1') })
export const env = schema.parse(import.meta.env)
EOF

w frontend/src/lib/utils.ts <<'EOF'
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)) }
EOF

w frontend/src/lib/api-client.ts <<'EOF'
import axios from 'axios'
import { env } from '@/config/env'
export const TOKEN_KEY = 'app-token'
export const apiClient = axios.create({
  baseURL: env.VITE_API_BASE_URL,
  headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
})
apiClient.interceptors.request.use((config) => {
  const t = localStorage.getItem(TOKEN_KEY)
  if (t) config.headers.Authorization = `Bearer ${t}`
  // FormData: drop JSON default so the browser sets the multipart boundary.
  if (typeof FormData !== 'undefined' && config.data instanceof FormData) delete config.headers['Content-Type']
  return config
})
EOF

w frontend/src/lib/query-client.ts <<'EOF'
import { QueryClient } from '@tanstack/react-query'
export const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 300000, retry: 1 } } })
EOF

w frontend/src/index.css <<'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;
/* TODO: port the approved theme.css tokens here (brand palette -> shadcn HSL vars). */
@layer base {
  :root {
    --background: 210 40% 98%;
    --foreground: 222 47% 11%;
    --card: 0 0% 100%;
    --primary: 354 81% 51%;        /* brand accent */
    --primary-foreground: 0 0% 100%;
    --border: 214 32% 91%;
    --accent: 210 40% 96%;
    --radius: 0.875rem;
  }
  body { @apply bg-background text-foreground; font-family: Inter, system-ui, sans-serif; }
}
EOF

w frontend/src/main.tsx <<'EOF'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createRouter, RouterProvider } from '@tanstack/react-router'
import { routeTree } from './route-tree.gen'
import './index.css'
const router = createRouter({ routeTree })
declare module '@tanstack/react-router' { interface Register { router: typeof router } }
createRoot(document.getElementById('root')!).render(<StrictMode><RouterProvider router={router} /></StrictMode>)
EOF

w frontend/src/app/routes/__root.tsx <<'EOF'
import { createRootRoute, Outlet } from '@tanstack/react-router'
import { QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { queryClient } from '@/lib/query-client'
export const Route = createRootRoute({ component: () => (
  <QueryClientProvider client={queryClient}><Outlet /><Toaster position="top-center" /></QueryClientProvider>
)})
EOF

w frontend/src/app/routes/index.tsx <<EOF
import { createFileRoute } from '@tanstack/react-router'
export const Route = createFileRoute('/')({ component: () => (
  <div className="grid min-h-screen place-items-center text-center">
    <div>
      <h1 className="text-3xl font-extrabold">${APP}</h1>
      <p className="mt-2 text-sm opacity-70">fastreact skeleton. Build features per the skill references.</p>
    </div>
  </div>
)})
EOF

w README.md <<EOF
# ${APP}

Full-stack app (FastAPI + React) scaffolded with the \`fastreact\` skill.

\`\`\`bash
cp .env.example .env   # fill secrets
make up && make logs
\`\`\`
Frontend http://localhost:8082 · API http://localhost:8000/api/v1 (docs /docs).

Next: build backend (models/schemas/services/routers/auth/s3/seed) and frontend
(features/auth, shell, feature slices) per the fastreact skill references.
EOF

echo ""
echo "Scaffolded '${APP}' at ${DIR}"
echo "Next: cp .env.example .env (fill secrets) ; make up ; then build domain code per the fastreact references."
