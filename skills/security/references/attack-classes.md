# Attack classes

Layer these on top of STRIDE × OWASP. Pick classes that match the surfaces listed in Scope; skip the rest. Distilled from Cloudflare `security-audit-skill` attack-class companions (MIT) - keep claims evidence-gated per SKILL.md.

## Injection

Trace untrusted input from entry to dangerous sink (SQL, HTML, shell, templates, paths, redirects, deserialization, LDAP/XPath, log sinks).

- Follow **indirect** paths: stored safely, then reused dangerously elsewhere.
- Inject via field **names**, keys, headers, metadata - not only values.
- Secondary systems: logs, caches, search indexes, analytics.

## Access control

Existence of a permission check is not enough - verify the *right* permission for the *right* resource via the *right* path.

- Alternate path to the same state change with a weaker gate
- Body/query fields that override what authz intended to restrict
- Authn without authz; inconsistent checks across bulk/export/import
- Split auth-bypass vs authorization-logic when the model is complex

## Resource and file handling

- Path traversal (symlinks, encoding, null bytes)
- SSRF (redirects, DNS rebinding, URL-parser differentials) - see also `stride-owasp.md`
- Unsafe deserialization, zip slip, temp-file races (TOCTOU)

## Cryptography and secrets

- Weak RNG for tokens/keys; hardcoded secrets; secrets in logs/URLs/errors
- Broken KDF, missing MAC, nonce reuse, timing-unsafe compares
- Crypto fail-open (error path disables crypto)

## Business logic

Scanners miss these; hunt by hand per major workflow:

- **State machines** - skip / reverse / replay / partial-failure without rollback
- **Races** - check-then-act double-spend, double-approve, lost updates
- **Numeric abuse** - negative/zero/overflow/precision/type coercion
- **Wrong business check** - permission exists but not for this rule
- **Implicit trust** - "validated on the way in" via a different writer
- **Time** - expiry boundaries, clock skew, timezone splits
- **Defaults** - missing config, feature-flag off, dependency down, mid-migration

## Feature abuse and data leakage

Legitimate features used off-label:

- Export/backup as exfiltration above the caller's access
- Import/restore as injection or overwrite bypassing validation
- Search/filter/sort as existence or value oracles
- Enumeration via error/timing/status differentials (reset, invite, register)
- Preview/draft/staging leakage (tokens, sitemaps, CDN cache headers)
- Notification/webhook URL → SSRF

## Chained / second-order

- Multi-step: only connect concrete outputs to later trust decisions
- Cross-component: A's guarantee ≠ what B assumes (truncation, coercion, tenant scope)
- Second-order use: safe-at-rest becomes path/URL/regex/template later
- Capability growth after refresh/delegation/role change/composition
- Ordering windows: soft-delete, revoke/cache, check/use, validate/consume
- Restore/undelete must re-apply current ownership and authz

## Obvious things (do not skip)

Hardcoded secrets; TODO/FIXME that disable auth; debug/dev gates; seed creds in prod; unprotected `/debug` `/admin` `/metrics` `/env`; committed `.env`/`*.pem`; `.gitignore` gaps; unpinned deps with known CVEs; commented-out auth checks; secrets still in git history.

## Wildcard

After assigned classes, hunt boring/experimental/compatibility/fallback code and API shapes the UI never exercises. Same evidence bar - anomalies are leads, not findings, until the invariant is settled.
