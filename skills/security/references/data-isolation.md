# Data isolation and lifecycle

Use when the target is multi-tenant or access-controlled, derives search/cache/analytics copies, exports/restores, migrates, or promises deletion/revocation. Distilled from Cloudflare `security-audit-skill` DATA-ISOLATION-AND-LIFECYCLE (MIT).

## Core discipline

- A tenant/owner **field on a record is not isolation** - find the query/key/path/RLS that enforces it on every read and write path.
- Trace **derived copies** - primary ACL can drift from search, cache, analytics, export, preview, logs, replicas, backups.
- Deletion/revocation are **lifecycle contracts** across current, historical, cached, indexed, exported, restored, and queued copies.
- Privacy preference ≠ vulnerability; require an explicit access or deletion boundary and an unauthorized reader/operation.

## Tenant and object isolation

- Missing tenant binding on read/update/delete/list/count/bulk; body-supplied identity
- Cache/object/search/temp keys that omit tenant → collision across principals
- Policy vs query disagreement (ORM scopes, raw/bypass clients, joins, `unscoped`)
- Signed URLs / object keys / version IDs that outlive ACL changes or over-scope the issuer

## Derived data

- Search/cache/index ACL drift after primary ACL or lifecycle change
- Analytics/logs/traces as alternate readers with broader access or longer retention
- Counts, filters, ordering, errors, timings as enumeration oracles

## Export, backup, restore, migration

- Export/backup includes other tenants, secret fields, soft-deleted or history above access
- Import/restore bypasses owner/schema/ACL/validation or writes into foreign tenants
- Migration defaults / ID collisions / dual-read paths with inconsistent tenants
- Backup/replica environments with broader identity than primary (often `needs_validation`)

## Deletion and revocation

- Soft-delete / tombstone bypass via direct lookup, search, jobs, or object links
- Stale auth after membership/ACL/secret revoke (sessions, caches, jobs)
- Queued work recreating data after primary delete
- Restore/undelete reintroducing credentials or permissions current policy forbids

## Validation

1. Name attacker, protected data, affected owner/tenant, alternate path, unauthorized effect.
2. Cite intended policy and the path that omits it; confirm no other layer enforces the same rule.
3. Prefer local dummy tenants / non-sensitive fixtures; stop at minimum observable cross-scope effect.
4. External CDN/object-store/replica facts → `needs_validation` with an exact owner check.
