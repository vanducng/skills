---
name: herd-worktree
description: "Set up an isolated git worktree for a Laravel project served by Laravel Herd (Pro-aware). Composes vd:worktree for the worktree/.env/port mechanics, then adds the Herd layer: link + scheme-correct site (HTTPS via herd secure when the source is secured), .env rewrite (APP_URL, SESSION_DOMAIN, Sanctum — only when present), opt-in per-worktree database isolation, Vite TLS/CORS, then hands finishing to vd:ship / vd:git. Triggers: 'herd-worktree', 'herd worktree', 'laravel herd worktree', 'isolate a Laravel feature branch', 'work on this Laravel branch with Herd'."
license: MIT
metadata:
  author: vanducng
  version: "1.1.0"
---

# Laravel Herd Worktree

Spin up an isolated, runnable copy of a Laravel project on its own Herd site for feature-branch work — without colliding with your main checkout or, on **Herd Pro**, your shared dev database.

**Announce at start:** "Using laravel-herd-worktree to set up an isolated Laravel + Herd workspace."

## Design: this is a thin Herd layer on top of `vd:worktree`

Do **not** reinvent worktree mechanics. `vd:worktree` already creates the worktree under `.worktrees/<repo>-<feature>/`, copies all `.env*` (nested included), assigns a deterministic 10-port block (`.env.worktree` → `WORKTREE_PORT_BASE`), keeps `.git/info/exclude` clean, anchors agent artifacts to the main checkout, and enters the worktree. This skill only adds what Herd needs and then defers finishing to `vd:ship` / `vd:git`.

| Concern | Owner |
|---|---|
| Worktree + branch + `.env` copy + ports | **`vd:worktree`** |
| Herd site (link/secure), `.env` URL/session rewrite, DB isolation, Vite | **this skill** |
| Commit / push / PR / version | **`vd:ship`** / **`vd:git`** |

## Prerequisites

- **Laravel Herd** (Pro adds shared MySQL/Postgres/Redis services — relevant to DB isolation below). macOS.
- **Vite** + **npm** frontend (adjust if yarn/pnpm).
- **Laravel Sanctum** only if the project uses it (steps below are conditional).

## Setup

### 1. Create the worktree via `vd:worktree`

Detect the branch (ticket key is authoritative), then:

```bash
node $HOME/.claude/skills/worktree/scripts/worktree.cjs create "<branch>" --no-prefix --json
```

Use the canonical path `$HOME/skills/skills/worktree/scripts/worktree.cjs` if this repo is at `$HOME/skills`; otherwise the installed symlink above. Parse the JSON for the worktree `path` and `portBase`, then move the session into the worktree (per the `sessionSwitch` block). The `.env` is already copied — you only *rewrite* it below.

```bash
PROJECT_NAME=$(basename "$(git rev-parse --show-toplevel)")   # main repo name
SANITIZED_BRANCH=$(echo "$BRANCH_NAME" | tr '/' '-')
SITE_NAME="$PROJECT_NAME-$SANITIZED_BRANCH"                    # matches .worktrees/<repo>-<feature>
```

### 2. Link to Herd — match the source site's scheme

Detect whether the **source** project is secured (don't assume HTTP):

```bash
herd links | grep -E "\b$PROJECT_NAME\b"     # SSL column, or:
grep '^APP_URL=' /path/to/main/.env          # https:// ⇒ secured
```

```bash
cd <worktree-path>
herd link "$SITE_NAME"
# If the source is HTTPS (Herd Pro default for team projects):
herd secure "$SITE_NAME"     # ⇒ https://$SITE_NAME.test
# Only if the source is plain HTTP: skip herd secure (HTTP matches the Vite dev server)
```

> Forcing HTTP on a project that is normally HTTPS causes scheme/cookie mismatches. Mirror the source.

### 3. Rewrite the worktree `.env` (conditionally)

`SCHEME` = `https` if secured, else `http`. Edit **only** keys that exist in the source `.env`:

```bash
ENV=<worktree-path>/.env
sed -i '' "s|^APP_URL=.*|APP_URL=$SCHEME://$SITE_NAME.test|" "$ENV"

# SESSION_DOMAIN: only set if the source set a real domain (skip when it's null/empty — single-host).
grep -qE '^SESSION_DOMAIN=.+' /path/to/main/.env && [ "$(grep '^SESSION_DOMAIN=' /path/to/main/.env)" != "SESSION_DOMAIN=null" ] \
  && sed -i '' "s|^SESSION_DOMAIN=.*|SESSION_DOMAIN=$SITE_NAME.test|" "$ENV"

# Sanctum: only if present.
grep -q '^SANCTUM_STATEFUL_DOMAINS=' "$ENV" \
  && sed -i '' "s|^SANCTUM_STATEFUL_DOMAINS=\(.*\)|SANCTUM_STATEFUL_DOMAINS=\1,$SITE_NAME.test|" "$ENV"

# Secure-cookie flag only matters for HTTP.
[ "$SCHEME" = "http" ] && echo "SESSION_SECURE_COOKIE=false" >> "$ENV"
```

### 4. Database — isolate or share (Herd Pro footgun)

On Herd Pro the worktree's copied `.env` points at the **same** shared DB as main. A feature branch running `migrate` / `migrate:fresh` / seeders would mutate your main dev database. Ask:

```
AskUserQuestion:
  question: "This worktree will run migrations against DB_DATABASE. Isolate it?"
  header: "Database"
  options:
    - label: "Isolate (Recommended)"  → create a per-worktree DB, rewrite DB_DATABASE
    - label: "Share main DB"          → reuse the same DB (read-only / no migrations)
```

If **Isolate** (MySQL example; mirror for Postgres):

```bash
DBNAME=$(grep '^DB_DATABASE=' "$ENV" | cut -d= -f2)_$SANITIZED_BRANCH
mysql -h 127.0.0.1 -u "$(grep '^DB_USERNAME=' "$ENV" | cut -d= -f2)" -e "CREATE DATABASE IF NOT EXISTS \`$DBNAME\`"
sed -i '' "s|^DB_DATABASE=.*|DB_DATABASE=$DBNAME|" "$ENV"
# (migrate in step 6)
```

### 5. Vite — scheme-aware

```bash
ls <worktree-path>/vite.config.ts <worktree-path>/vite.config.js 2>/dev/null   # detect either
```

- **HTTPS site:** `laravel-vite-plugin` auto-detects the Herd TLS cert created by `herd secure` and serves Vite over HTTPS on the right host — leave it to the plugin. Add `server: { cors: true }` only if you actually see cross-origin blocks.
- **HTTP site:** ensure `server: { host: 'localhost', cors: true }` (do **not** use `0.0.0.0`).

### 6. Register teardown hook (so `vd:worktree clean`/`remove` cleans Herd + DB)

`vd:worktree` runs `.worktree/hooks/pre-remove` inside the worktree on **both** `remove` and `clean` (env exported: `WORKTREE_NAME`, `WORKTREE_PATH`, `WORKTREE_SOURCE`, …). Write one at setup so the Herd site and any isolated DB are never orphaned — `worktree clean` then handles Laravel teardown for free:

```bash
mkdir -p <worktree-path>/.worktree/hooks
cat > <worktree-path>/.worktree/hooks/pre-remove <<'EOF'
#!/usr/bin/env bash
# Herd + DB teardown — runs on `vd:worktree remove` and `clean`. Failure warns, never blocks.
set -u
herd unlink "$WORKTREE_NAME" 2>/dev/null || true
pkill -f "node.*vite.*$WORKTREE_NAME" 2>/dev/null || true
# Drop the DB only if this worktree was isolated (its DB differs from the source's).
DB=$(grep -m1 '^DB_DATABASE=' "$WORKTREE_PATH/.env" 2>/dev/null | cut -d= -f2)
SRC_DB=$(grep -m1 '^DB_DATABASE=' "$WORKTREE_SOURCE/.env" 2>/dev/null | cut -d= -f2)
if [ -n "${DB:-}" ] && [ "$DB" != "${SRC_DB:-}" ]; then
  mysql -h 127.0.0.1 -u root -e "DROP DATABASE IF EXISTS \`$DB\`" 2>/dev/null || true
fi
EOF
chmod +x <worktree-path>/.worktree/hooks/pre-remove
```

The DB drop is guarded — it never touches the shared/source database, only a per-worktree one created in step 4.

### 7. Install, migrate, run

```bash
cd <worktree-path>
composer install --no-interaction          # worktrees don't share vendor/
npm install                                # …or node_modules/
php artisan config:clear && php artisan cache:clear
[ -n "$DBNAME" ] && php artisan migrate     # only when DB was isolated; add --seed if wanted

pkill -f "node.*vite" 2>/dev/null; rm -f public/hot   # free a stale Vite/hot file
npm run build     # or keep `npm run dev` running while browsing through Herd
```

Site: `$SCHEME://$SITE_NAME.test`.

## Finishing — delegate, don't reinvent

When work is done, **route to the existing skills** rather than a bespoke PR flow:

- **Ship it:** `vd:ship` (test → review → version → PR) or `vd:git` for a single conventional commit + push from the worktree branch.
- **Bring changes into main checkout:** `git merge <branch> --no-commit --no-ff` from the main tree, review, commit.

Then clean up through `vd:worktree` — the pre-remove hook from step 6 does the Herd unlink + isolated-DB drop automatically:

```bash
node $HOME/.claude/skills/worktree/scripts/worktree.cjs remove "$SITE_NAME"   # one worktree: hook → branch → metadata
# or sweep all merged/stale worktrees at once (each runs its own teardown hook):
node $HOME/.claude/skills/worktree/scripts/worktree.cjs clean --yes
```

Because teardown lives in the worktree's `pre-remove` hook, `vd:worktree clean` tears down the Herd site and isolated DB for **every** swept worktree — no orphaned `.test` sites or leftover databases. (Stop Vite first if it's still running: `pkill -f "node.*vite"`.)

## Herd Pro notes

- **Shared services:** Pro's MySQL/Postgres/Redis are shared across all sites — DB isolation (step 4) is the main safeguard; Redis/queue can collide too (use a per-worktree `REDIS_PREFIX` / `DB_REDIS` if the branch hits queues).
- **HTTPS is the Pro default** for team projects — mirror it (steps 2–3), don't force HTTP.
- **Per-site PHP:** `herd isolate <php-version>` inside the worktree if it needs a different PHP than the global default.

## Common issues

| Symptom | Cause → Fix |
|---|---|
| 401 on API routes | Sanctum domain missing → add `$SITE_NAME.test` to `SANCTUM_STATEFUL_DOMAINS`, `php artisan config:clear` |
| "Cookie rejected for invalid domain" | `SESSION_DOMAIN` mismatch → set to `$SITE_NAME.test` (or leave null for single host), `config:clear`, clear browser cookies |
| Mixed Content (HTTPS page, HTTP assets) | Vite served HTTP under an HTTPS site → confirm `herd secure` ran and `laravel-vite-plugin` sees the cert; restart `npm run dev` |
| CORS blocked (HTTP site) | Vite `host: '0.0.0.0'` → set `host: 'localhost'`, `cors: true`, restart |
| Migrations hit the wrong/shared DB | `.env` still points at main DB → isolate (step 4) and rewrite `DB_DATABASE` |
| Vite manifest not found | no `public/build/manifest.json` and no Vite dev server → `npm install`, then `npm run build` (or keep `npm run dev` running) |
| Assets not loading / wrong port | stale Vite → `pkill -f "node.*vite"`, `rm -f public/hot`, `npm run dev` from the worktree |
| Missing vendor/ or node_modules/ | worktrees don't share them → `composer install` / `npm install` in the worktree |

## Checklist

- [ ] Worktree created via `vd:worktree` (`.worktrees/$SITE_NAME`, `.env` copied, ports assigned)
- [ ] `herd link` done; **scheme matches source** (secured ⇒ `herd secure`)
- [ ] `.env` rewritten: `APP_URL` (correct scheme), `SESSION_DOMAIN`/Sanctum only if applicable
- [ ] Database decision made (isolated DB + `DB_DATABASE` rewritten, or explicitly sharing)
- [ ] `.worktree/hooks/pre-remove` written (Herd unlink + isolated-DB drop on `worktree remove`/`clean`)
- [ ] `vite.config.{ts,js}` correct for the scheme
- [ ] `composer install` + `npm install` done; `npm run build` done or `npm run dev` running; migrations run if isolated
- [ ] Site reachable at `$SCHEME://$SITE_NAME.test`

## CRITICAL: working directory after setup

All subsequent work (edits, artisan, tests, git) MUST use the worktree path. `vd:worktree` enters it by default; stay there. The main checkout is a different copy — editing it changes the wrong files.

## Integration

- **Composes:** `vd:worktree` (mechanics), `vd:ship` / `vd:git` (finishing).
- **Pairs with:** `vd:cook` / `vd:fix` (implement in the worktree).
