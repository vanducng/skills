# Local setup — Docker Compose

Three services. Backend migrates + seeds on start; frontend builds in-container and serves via nginx.

## docker-compose.yml (shape)
```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment: { POSTGRES_USER: ${POSTGRES_USER}, POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}, POSTGRES_DB: ${POSTGRES_DB} }
    healthcheck: { test: ["CMD-SHELL","pg_isready -U $${POSTGRES_USER}"], interval: 5s, retries: 10 }
    volumes: [pgdata:/var/lib/postgresql/data]
    ports: ["5436:5432"]          # pick a FREE host port
  backend:
    build: { context: ./backend, dockerfile: Dockerfile.app }
    env_file: .env
    environment: { POSTGRES_HOST: postgres, POSTGRES_PORT: 5432 }
    depends_on: { postgres: { condition: service_healthy } }
    ports: ["8000:8000"]
    healthcheck: { test: ["CMD","python","-c","import urllib.request;urllib.request.urlopen('http://localhost:8000/api/v1/livez')"], interval: 10s, retries: 12 }
  frontend:
    build: { context: ./frontend, args: { VITE_API_BASE_URL: ${VITE_API_BASE_URL} } }
    ports: ["8082:80"]            # pick a FREE host port
    depends_on: { backend: { condition: service_healthy } }
volumes: { pgdata: {} }
```

## Ports — check before you bind
Other local stacks commonly hold 5173, 5432–5435, 8000, 8080. Before `make up`:
```bash
for p in 5173 8000 8080 5432 5436; do lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null && echo "$p busy" || echo "$p free"; done
```
Set the frontend host port + `VITE_API_BASE_URL` + backend `CORS_ORIGINS` to agree (browser hits the published backend port directly).

## backend/entrypoint.sh
```sh
#!/usr/bin/env sh
set -e
[ "$RUN_MIGRATIONS" != "0" ] && alembic upgrade head
[ "$SEED_ON_START" = "1" ] && (python -m app.tasks.seed || true)
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## backend/Dockerfile.app
uv builder stage runs `uv sync --no-dev` (no committed lock needed); final `python:3.12-slim`, non-root, copies `.venv` + `app` + `migrations` + `alembic.ini` + `entrypoint.sh`; `ENV PATH=/app/.venv/bin:$PATH`; HEALTHCHECK hits `/api/v1/livez`; `ENTRYPOINT ["./entrypoint.sh"]`. Pin `backend/.python-version` to 3.12 so uv matches the image.

## frontend/Dockerfile + nginx.conf
Multi-stage: `node:22-slim` → `npm ci && npm run build` with `ARG VITE_API_BASE_URL`, then `nginx:alpine` serving `dist/` + `nginx.conf` (`try_files $uri /index.html`; proxy `/api/` → `http://backend:8000`).

## Makefile targets
`up` (= `docker compose up -d --build`), `down`, `clean` (= `down -v`, resets DB), `logs`, `ps`, `seed` (`docker compose exec backend python -m app.tasks.seed`), `migrate`, `be-test`, `fe-test`.

## .env (gitignored) keys
`APP_ENV, POSTGRES_HOST/PORT/USER/PASSWORD/DB, SECRET_KEY, JWT_SECRET, JWT_EXPIRY_HOURS, CORS_ORIGINS, GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI/ALLOWED_DOMAIN, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET, S3_PREFIX, ADMIN_EMAIL, ADMIN_PASSWORD, SEED_ON_START, VITE_API_BASE_URL`.

## Run
```bash
cp .env.example .env   # fill secrets
make up && make logs   # migrate + seed run automatically
make clean             # wipe DB volume to re-seed from scratch
```
Access: frontend `http://localhost:<fe-port>`, API `http://localhost:8000/api/v1` (docs `/docs`).

## Iteration notes
- Backend code is baked into the image: rebuild (`docker compose up -d --build backend`) to pick up changes.
- Frontend asset hashes change per build; if the browser shows stale JS, hard-reload or use a fresh browser context.
- `docker compose build` (bare) may be blocked by context hooks; use `docker compose up -d --build` (the `--build` flag form works).
