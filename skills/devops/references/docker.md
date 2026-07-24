# Docker & Docker Compose

## Dockerfile best practices

Order layers cheapest-changing first so the cache stays warm. Copy dependency manifests before source, install, then copy code.

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev        # deps layer - cached until manifests change
COPY . .
ENV NODE_ENV=production
EXPOSE 3000
USER node                     # non-root
CMD ["node", "server.js"]
```

**Rules that matter:**
- **Multi-stage builds for production** - build in a fat image, copy only artifacts into a slim/`scratch` runtime. No build tools or source in the final image.
- **Pin specific base tags** (`node:20.11-alpine3.19`), never `latest`.
- **Run as non-root** (`USER`); `COPY --chown` to set ownership.
- **`.dockerignore`** to keep `node_modules`, `.git`, `.env`, logs out of the build context.
- Add a `HEALTHCHECK`; set resource limits at run time; keep images small (<500MB target).

**Multi-stage example (Go → scratch):**
```dockerfile
FROM golang:1.24-alpine AS build
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /main .

FROM scratch
COPY --from=build /main /main
CMD ["/main"]
```

For Node/Python: build deps in stage 1, copy `dist` + installed packages into a fresh slim runtime, add a non-root user.

## Building & running

```bash
docker build -t myapp:1.0 .
docker build --target build -t myapp:dev .        # stop at a stage
docker buildx build --platform linux/amd64,linux/arm64 -t myapp:1.0 .  # multi-arch
docker run -d --name myapp -p 8080:3000 -e NODE_ENV=production \
  --memory 512m --cpus 0.5 myapp:1.0
docker logs -f myapp
docker exec -it myapp /bin/sh
docker image history myapp:1.0                     # inspect layer sizes
```

## Docker Compose

Services on the same network reach each other by service name. Prefer `docker compose` (v2, plugin) over `docker-compose`.

```yaml
services:
  web:
    build: .
    ports: ["3000:3000"]
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/app
    depends_on: [db]
    restart: unless-stopped
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: app
    volumes: [postgres_data:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5
volumes:
  postgres_data:
```

```bash
docker compose up -d --build
docker compose logs -f web
docker compose exec db psql -U user -d app
docker compose config          # validate/render
docker compose down --volumes   # stop + drop volumes
```

**Environment layering:** `compose.yml` (base) + auto-loaded `compose.override.yml` (dev: bind-mount source, debug env) vs explicit `-f compose.yml -f compose.prod.yml up -d` (prod: pinned image, `restart: always`, replicas, resource limits). Health checks on every service, JSON logging with `max-size`/`max-file`, named volumes for persistence, custom networks for isolation.

## Security & troubleshooting

- **Scan images:** `docker scout cves myapp:1.0` or Trivy. Non-root user, minimal base, no secrets in layers (they persist in history - use build secrets/`--mount=type=secret`).
- **Container exits immediately:** `docker logs myapp`; override entrypoint to poke around: `docker run -it --entrypoint /bin/sh myapp`.
- **Can't connect:** `docker port myapp`, `docker network inspect`, check the container actually listens on `0.0.0.0` not `127.0.0.1`.
- **Out of disk:** `docker system df` then `docker system prune -a` / `docker volume prune` (destructive - confirm first).
- **Stale build:** `docker build --no-cache` / `docker builder prune`.
