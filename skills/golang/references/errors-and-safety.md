# Errors, Safety & Security

## Error handling

1. **Always check returned errors** — never `_` them away.
2. **Wrap with context**: `fmt.Errorf("querying user %s: %w", id, err)`. Use `%w` internally (preserves the chain), `%v` at system boundaries (severs it so you don't leak internals).
3. **Error strings**: lowercase, no trailing punctuation, low-cardinality — don't interpolate IDs/paths into the message; attach them as structured attributes at the log site. This lets APM/log aggregators group errors.
4. **`errors.Is` / `errors.As`** to inspect, never `==` or a raw type assertion. `errors.Join` (1.20+) to combine independent errors.
5. **Log OR return, never both.** Duplicate logs cascade up the chain. Log once at the top level; propagate with context everywhere else.
6. **Sentinel errors** for expected conditions (`var ErrNotFound = errors.New("...")` — preallocated, comparable with `errors.Is`); **custom error types** when the error must carry data (`errors.As` into a typed target).
7. **Panic is for unrecoverable bugs**, not expected failures. Recover only at goroutine boundaries. `.Close()` errors in a `defer` may go unchecked.
8. Translate internal errors to user-safe messages at the boundary; log the technical detail separately.

```go
func GetUser(ctx context.Context, id string) (*User, error) {
    var u User
    if err := db.GetContext(ctx, &u, "SELECT id, name FROM users WHERE id = $1", id); err != nil {
        if errors.Is(err, sql.ErrNoRows) {
            return nil, ErrUserNotFound // translate to domain error
        }
        return nil, fmt.Errorf("querying user %s: %w", id, err)
    }
    return &u, nil
}
```

For errors that need stack traces, tenant/user context, and APM grouping in production, reach for `samber/oops` — see **gostack**.

## Safety (defensive coding)

Prevents your own mistakes — panics and silent corruption in normal (non-adversarial) code.

**Nil traps:**
- An interface is `nil` only when *both* type and value are nil. Returning a typed nil pointer (`var h *MyHandler; return h`) yields a non-nil interface. Return an untyped `nil` explicitly for the nil case.
- **Writing to a nil map panics.** Indexing a nil slice panics. Sending/receiving on a nil channel blocks forever. Initialize before use; lazy-init map fields in methods (`if r.items == nil { r.items = make(...) }`).

**Slice aliasing — the append trap:** `append` reuses the backing array when capacity allows, so two slices silently share memory. Force a copy with the full three-index slice: `b := append(a[:len(a):len(a)], 4)`.

**Numeric:**
- Narrowing conversions truncate silently (`int32(3_000_000_000)` wraps negative). Bounds-check against `math.MaxInt32`/`MinInt32` first.
- Floats aren't exact: compare with an epsilon (`math.Abs(a-b) < 1e-9`), not `==`.
- Integer division by zero panics — guard it. Float division yields `±Inf`/`NaN`.

**Resources:**
- `defer` runs at *function* exit, not loop iteration — `defer f.Close()` inside a loop accumulates open files. Extract the loop body to a function.

**Copies & init:**
- Exported functions returning internal slices/maps should return **defensive copies** (`slices.Clone`, `maps.Clone`) — otherwise callers mutate your internals.
- Design useful zero values; `sync.Once` (or `OnceValue`/`OnceFunc`, 1.21+) for lazy one-time init.
- Comma-ok every type assertion; maps must not be accessed concurrently (data race → hard crash).

Machine-enforced by: `errcheck`, `forcetypeassert`, `nilerr`, `govet`, `staticcheck`.

## Security

Defense in depth — validate at trust boundaries, secure defaults, lean on the stdlib's security-aware APIs. Ask: where does untrusted data enter, what can the attacker control, what's the blast radius.

| Risk | Defense |
| --- | --- |
| SQL injection | Parameterized queries (`$1` / `?`) — never string-concat user input; allowlist dynamic column names |
| Command injection | `exec.Command(bin, args...)` with separate args — never `bash -c` with concatenation |
| XSS | `html/template` auto-escaping (not `text/template` for HTML) |
| Path traversal | `os.Root` (1.24+), `filepath.Clean`, scope to a root |
| Weak randomness | `crypto/rand` for tokens/keys — never `math/rand` |
| Timing attacks | `crypto/subtle.ConstantTimeCompare` for secret comparison |
| Weak crypto | AES-GCM (authenticated); Argon2id/bcrypt for passwords — never MD5/SHA1, never roll your own |
| Hardcoded secrets | Env vars or a secret manager; per-environment secrets; never commit credentials |
| Info disclosure | Return generic errors to clients, log detail server-side |

- Never trust client-supplied headers (`X-Forwarded-For`, `X-Is-Admin`) or client-side authz — verify server-side on every handler.
- Fail closed: always check crypto/auth errors, never silently proceed unencrypted.
- Tooling: `gosec ./...` (SAST), `govulncheck ./...` (reachable CVEs), `go test -race ./...`, fuzzing (`go test -fuzz=Fuzz`). Security linters (`bodyclose`, `sqlclosecheck`) must not be suppressed without strong justification.

When a finding sits behind upstream validation, don't dismiss it — downgrade severity and note the protecting layer with an inline comment so future audits don't re-flag it.
